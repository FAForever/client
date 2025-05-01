import logging
import os
from enum import Enum
from enum import auto
from typing import Callable

from PyQt6 import QtCore
from PyQt6 import QtNetwork
from PyQt6 import QtWidgets

from src.downloadManager import FileDownload
from src.downloadManager import ZipDownloadExtract
from src.util import capitalize

logger = logging.getLogger(__name__)


class VaultDownloadResult(Enum):
    SUCCESS = auto()
    CANCELED = auto()
    DL_ERROR = auto()
    UNKNOWN_ERROR = auto()


class VaultDownloadDialog(object):

    def __init__(
            self,
            dler: FileDownload | ZipDownloadExtract,
            title: str,
            label: str,
            silent: bool = False,
    ) -> None:
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
            QtCore.Qt.WindowType.CustomizeWindowHint | QtCore.Qt.WindowType.WindowTitleHint,
        )
        self._progress.setAutoReset(False)
        self._progress.setModal(1)
        self._progress.canceled.connect(self._dler.cancel)

        progressBar = QtWidgets.QProgressBar(self._progress)
        progressBar.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._progress.setBar(progressBar)

        self.progress_measure_interaval = 250
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.progress_measure_interaval)
        self.timer.timeout.connect(self.updateLabel)
        self.bytes_prev = 0

    def updateLabel(self) -> None:
        label_text = f"{self.label}\n\n{self.get_download_progress_mb()}"
        speed_text = f"({self.get_download_speed()} MB/s)"
        if self._dler.bytes_total > 0:
            label_text = f"{label_text}/{self.get_download_size_mb()} MB\n\n{speed_text}"
        else:
            label_text = f"{label_text} MB {speed_text}"
        self._progress.setLabelText(label_text)

    def get_download_speed(self) -> float:
        bytes_diff = self._dler.bytes_progress - self.bytes_prev
        self.bytes_prev = self._dler.bytes_progress
        return round(bytes_diff * (1000 / self.progress_measure_interaval) / 1024 / 1024, 2)

    def get_download_progress_mb(self) -> float:
        return round(self._dler.bytes_progress / 1024 / 1024, 2)

    def get_download_size_mb(self) -> float:
        return round(self._dler.bytes_total / 1024 / 1024, 2)

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

    def _finished(self, dler: FileDownload | ZipDownloadExtract) -> None:
        self.timer.stop()
        self._progress.reset()
        self._set_result(dler)

    def _set_result(self, dler: FileDownload | ZipDownloadExtract) -> None:
        if dler.failed():
            if dler.canceled:
                self._result = VaultDownloadResult.CANCELED
                return
            elif dler.error:
                self._result = VaultDownloadResult.DL_ERROR
                return
            else:
                logger.error('Unknown download error')
                self._result = VaultDownloadResult.UNKNOWN_ERROR
                return

        self._result = VaultDownloadResult.SUCCESS
        return


# FIXME - one day we'll do it properly
_global_nam = QtNetwork.QNetworkAccessManager()


def _download_asset(
        dler: FileDownload | ZipDownloadExtract,
        category: str,
        silent: bool,
        label: str = "",
) -> VaultDownloadResult:
    ddialog = VaultDownloadDialog(dler, f"Downloading {category}", label, silent)
    result = ddialog.run()

    if result == VaultDownloadResult.CANCELED:
        logger.warning("%s Download canceled for: %s", category, dler.addr)
    if result in [
        VaultDownloadResult.DL_ERROR,
        VaultDownloadResult.UNKNOWN_ERROR,
    ]:
        logger.warning("Download failed. %s", dler.addr)
    return result


def downloadVaultAssetNoMsg(
        url: str,
        target_dir: str,
        exist_handler: Callable[[str, str], bool],
        name: str,
        category: str,
        silent: bool,
        request_params: dict | None = None,
        label: str = "",
) -> tuple[bool, Callable[[], None] | None]:
    """
    Download and unpack a zip from the vault, interacting with the user and
    logging things.
    """
    global _global_nam

    msg = None
    capit_cat = capitalize(category)

    if os.path.exists(os.path.join(target_dir, name)):
        proceed = exist_handler(target_dir, name)
        if not proceed:
            return False, msg

    os.makedirs(target_dir, exist_ok=True)
    dler = ZipDownloadExtract(target_dir, _global_nam, url, request_params)
    result = _download_asset(dler, capit_cat, silent, label or name)

    if result in [
        VaultDownloadResult.DL_ERROR,
        VaultDownloadResult.UNKNOWN_ERROR,
    ]:
        logger.warning("Vault download failed, %s is probably not in vault (or broken).", category)
        msg_title = "{} not downloadable".format(capit_cat)
        msg_text = (
            f"<b>This {category} was not found in the vault (or is broken).</b>"
            f"<br/>You need to get it from somewhere else in order to "
            f"use it."
        )

        def msg():
            QtWidgets.QMessageBox.information(None, msg_title, msg_text)

    return result == VaultDownloadResult.SUCCESS, msg


def downloadVaultAsset(
        url: str,
        target_dir: str,
        exist_handler: Callable[[str, str], bool],
        name: str,
        category: str,
        silent: bool,
) -> bool:
    ret, dialog = downloadVaultAssetNoMsg(url, target_dir, exist_handler, name, category, silent)
    if dialog is not None:
        dialog()
    return ret


def download_file(
        url: str,
        target_dir: str,
        name: str,
        category: str,
        silent: bool,
        request_params: dict | None = None,
        label: str = "",
) -> bool:
    """
    Basically a copy of downloadVaultAssetNoMsg without zip
    """
    capit_cat = capitalize(category)

    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, name)

    dler = FileDownload(target_path, _global_nam, url, request_params)
    result = _download_asset(dler, capit_cat, silent, label or name)

    if result in [
        VaultDownloadResult.DL_ERROR,
        VaultDownloadResult.UNKNOWN_ERROR,
    ]:
        QtWidgets.QMessageBox.information(
            None,
            f"{capit_cat} not downloadable",
            f"<b>Failed to download {category} from</b><br/>{url}",
        )
    return result == VaultDownloadResult.SUCCESS
