from downloadManager import FileDownload
from PyQt5 import QtCore, QtNetwork, QtWidgets
import zipfile

class VaultDownloadDialog(object):
    # Result codes
    SUCCESS = 0
    CANCELED = 1
    DL_ERROR = 2
    UNKNOWN_ERROR = 3

    def __init__(self, dler, title, label, silent = False):
        self._silent = silent
        self._result = None

        self._dler = dler
        self._dler.cb_start = self._start
        self._dler.cb_progress = self._cont
        self._dler.cb_finished = self._finished
        self._dler.blocksize = 8192

        self._progress = QtWidgets.QProgressDialog()
        self._progress.setWindowTitle(title)
        self._progress.setLabelText(label)
        if not self._silent:
            self._progress.setCancelButtonText("Cancel")
        else:
            self._progress.setCancelButton(None)
        self._progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
        self._progress.setAutoReset(False)
        self._progress.setModal(1)
        self._progress.canceled.connect(self._dler.cancel)

    def run(self):
        self._progress.show()
        self._dler.run()
        self._dler.waitForCompletion()
        return self._result

    def _start(self, dler):
        self._progress.setMinimum(0)
        self._progress.setMaximum(dler.bytes_total)

    def _cont(self, dler):
        self._progress.setValue(dler.bytes_progress)
        self._progress.setMaximum(dler.bytes_total)
        QtWidgets.QApplication.processEvents()

    def _finished(self, dler):
        self._progress.reset()

        if not dler.succeeded():
            if dler.canceled:
                self._result = self.CANCELED
                return

            elif dler.error:
                self._result = self.DL_ERROR
                return
            else:
                self._result = self.UNKNOWN_ERROR
                return

        self._result = self.SUCCESS
        return

