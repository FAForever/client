import io
import logging
import os
import zipfile

from PyQt5 import QtCore, QtNetwork, QtWidgets

from downloadManager import FileDownload

logger = logging.getLogger(__name__)


class VaultDownloadDialog(object):
    # Result codes
    SUCCESS = 0
    CANCELED = 1
    DL_ERROR = 2
    UNKNOWN_ERROR = 3

    def __init__(self, dler, title, label, silent=False):
        self._silent = silent
        self._result = None

        self._dler = dler
        self._dler.start.connect(self._start)
        self._dler.progress.connect(self._cont)
        self._dler.finished.connect(self._finished)
        self._dler.blocksize = 8192

        self._progress = QtWidgets.QProgressDialog()
        self._progress.setWindowTitle(title)
        self.label = label
        self._progress.setLabelText(self.label)
        if not self._silent:
            self._progress.setCancelButtonText("Cancel")
        else:
            self._progress.setCancelButton(None)
        self._progress.setWindowFlags(
            QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint,
        )
        self._progress.setAutoReset(False)
        self._progress.setModal(1)
        self._progress.canceled.connect(self._dler.cancel)

        progressBar = QtWidgets.QProgressBar(self._progress)
        progressBar.setAlignment(QtCore.Qt.AlignCenter)
        self._progress.setBar(progressBar)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.updateLabel)
        self.bytes_prev = 0

    def updateLabel(self):
        self._progress.setLabelText(
            '{label}\n\n{downloaded} MiB ({speed} MiB/s)'
            .format(
                label=self.label,
                downloaded=self.getDownloadProgressMiB(),
                speed=self.getDownloadSpeed(),
            ),
        )

    def getDownloadSpeed(self):
        bytes_diff = self._dler.bytes_progress - self.bytes_prev
        self.bytes_prev = self._dler.bytes_progress
        return round(bytes_diff * 2 / 1024 / 1024, 2)

    def getDownloadProgressMiB(self):
        return round(self._dler.bytes_progress / 1024 / 1024, 2)

    def run(self):
        self.updateLabel()
        self.timer.start()
        self._progress.show()
        self._dler.run()
        self._dler.waitForCompletion()
        return self._result

    def _start(self, dler):
        self._progress.setMinimum(0)
        if dler.bytes_total > 0:
            self._progress.setMaximum(dler.bytes_total)
        else:
            self._progress.setMaximum(0)

    def _cont(self, dler):
        if dler.bytes_total > 0:
            self._progress.setValue(dler.bytes_progress)
            self._progress.setMaximum(dler.bytes_total)

        QtWidgets.QApplication.processEvents()

    def _finished(self, dler):
        self.timer.stop()
        self._progress.reset()

        if not dler.succeeded():
            if dler.canceled:
                self._result = self.CANCELED
                return

            elif dler.error:
                self._result = self.DL_ERROR
                return
            else:
                logger.error('Unknown download error')
                self._result = self.UNKNOWN_ERROR
                return

        self._result = self.SUCCESS
        return


# FIXME - one day we'll do it properly
_global_nam = QtNetwork.QNetworkAccessManager()


def downloadVaultAssetNoMsg(
    url, target_dir, exist_handler, name, category, silent,
):
    """
    Download and unpack a zip from the vault, interacting with the user and
    logging things.
    """
    global _global_nam
    msg = None
    msg_title = ""
    msg_text = ""
    output = io.BytesIO()
    capitCat = category[0].upper() + category[1:]

    dler = FileDownload(_global_nam, url, output)
    ddialog = VaultDownloadDialog(
        dler, "Downloading {}".format(category), name, silent,
    )
    result = ddialog.run()

    if result == VaultDownloadDialog.CANCELED:
        logger.warning("{} Download canceled for: {}".format(capitCat, url))

    if result in [
        VaultDownloadDialog.DL_ERROR,
        VaultDownloadDialog.UNKNOWN_ERROR,
    ]:
        logger.warning(
            "Vault download failed, {} probably not in vault "
            "(or broken).".format(category),
        )
        msg_title = "{} not downloadable".format(capitCat)
        msg_text = (
            "<b>This {} was not found in the vault (or is broken).</b>"
            "<br/>You need to get it from somewhere else in order to "
            "use it.".format(category)
        )

    if msg_title and msg_text:
        def msg():
            QtWidgets.QMessageBox.information(None, msg_title, msg_text)

    if result != VaultDownloadDialog.SUCCESS:
        return False, msg

    try:
        zfile = zipfile.ZipFile(output)
        # FIXME - nothing in python 2.7 that can do that
        dirname = zfile.namelist()[0].split(os.path.sep, 1)[0]

        if os.path.exists(os.path.join(target_dir, dirname)):
            proceed = exist_handler(target_dir, dirname)
            if not proceed:
                return False
        zfile.extractall(target_dir)
        logger.debug(
            "Successfully downloaded and extracted {} from: {}"
            .format(category, url),
        )
        return True, msg

    except BaseException:
        logger.error("Extract error")

        def msg():
            QtWidgets.QMessageBox.information(
                None,
                "{} installation failed".format(capitCat),
                (
                    "<b>This {} could not be installed (please report this {} "
                    "or bug).</b>".format(category, category)
                ),
            )
        return False, msg


def downloadVaultAsset(url, target_dir, exist_handler, name, category, silent):
    ret, dialog = downloadVaultAssetNoMsg(
        url, target_dir, exist_handler, name, category, silent,
    )
    if dialog is not None:
        dialog()

    return ret


def downloadFile(url, target_dir, name, category, silent):
    """
    Basically a copy of downloadVaultAssetNoMsg without zip
    """

    global _global_nam
    msg = None
    output = io.BytesIO()
    capitCat = category[0].upper() + category[1:]

    dler = FileDownload(_global_nam, url, output)
    ddialog = VaultDownloadDialog(
        dler, "Downloading {}".format(category), name, silent,
    )
    result = ddialog.run()

    if result == VaultDownloadDialog.CANCELED:
        logger.warning("{} Download canceled for: {}".format(capitCat, url))
    if result in [
        VaultDownloadDialog.DL_ERROR,
        VaultDownloadDialog.UNKNOWN_ERROR,
    ]:
        logger.warning("Download failed. {}".format(url))

        def msg():
            QtWidgets.QMessageBox.information(
                None,
                "{} not downloadable".format(capitCat),
                (
                    "<b>Failed to download {} from</b><br/>"
                    "{}".format(category, url)
                ),
            )

    if result != VaultDownloadDialog.SUCCESS:
        if msg:
            msg()
        return False

    if not os.path.exists(os.path.dirname(target_dir)):
        os.makedirs(os.path.dirname(target_dir))

    with open(target_dir, "w+b") as f:
        f.write(output.getvalue())

    return target_dir
