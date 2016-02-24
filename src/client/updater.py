import tempfile
import client
import subprocess

from decorators import with_logger
from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import QLabel
from PyQt4.QtCore import QUrl, QObject
from PyQt4.QtNetwork import QNetworkRequest, QNetworkReply


@with_logger
class ClientUpdater(QObject):
    def __init__(self, url):
        QObject.__init__(self)
        self.url = QUrl(url)
        self._progress = None
        self._network_manager = client.NetworkManager
        self._tmp = None
        self._req = None
        self._rep = None

    def exec_(self):
        result = QtGui.QMessageBox.question(None,
                                            "Update Needed",
                                            "Your version of FAF is outdated. You need to download and install the most recent version to connect and play.<br/><br/><b>Do you want to download and install the update now?</b><br/><br/><a href='https://github.com/FAForever/client/blob/develop/changelog.md'>See changes</a>",
                                            QtGui.QMessageBox.No,
                                            QtGui.QMessageBox.Yes)
        if result == QtGui.QMessageBox.Yes:
            self._setup_progress()
            self._tmp = tempfile.NamedTemporaryFile(mode='w+b',
                                                    suffix=".msi",
                                                    delete=False)
            self._req = QNetworkRequest(self.url)
            self._rep = self._network_manager.get(self._req)
            self._rep.setReadBufferSize(0)
            self._rep.downloadProgress.connect(self.on_progress)
            self._rep.finished.connect(self._run_installer)
            self._rep.error.connect(self.error)
            self._rep.readyRead.connect(self._buffer)
        else:
            QtGui.QApplication.quit()

    def error(self, code):
        self._logger.exception(self._rep.errorString())

    def _buffer(self):
        self._tmp.write(self._rep.read(self._rep.bytesAvailable()))

    def _run_installer(self):
        assert self._tmp
        assert self._rep.atEnd()
        if self._rep.error() == QNetworkReply.NoError:
            self._tmp.close()
            command = r'msiexec /i "{msiname}" & del "{msiname}"'.format(msiname=self._tmp.name)
            self._logger.debug(r'Running msi installation command: ' + command)
            subprocess.Popen(command, shell=True)
            self._progress.close()

    def on_progress(self, current, max):
        self._progress.setMaximum(max)
        self._progress.setValue(current)

    def cancel(self):
        self._rep.abort()
        QtGui.QApplication.quit()

    def _setup_progress(self):
        progress = QtGui.QProgressDialog()
        progress.setLabel(QLabel("Downloading update"))
        progress.setCancelButtonText("Cancel")
        progress.canceled.connect(self.cancel)
        progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint
                                | QtCore.Qt.WindowTitleHint)
        progress.setAutoClose(True)
        progress.setAutoReset(False)
        self._progress = progress
