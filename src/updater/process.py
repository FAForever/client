import os
import subprocess
import tempfile

from PyQt5.QtCore import QObject, QUrl, pyqtSignal
from PyQt5.QtNetwork import QNetworkReply, QNetworkRequest

import client
from decorators import with_logger


@with_logger
class ClientUpdater(QObject):

    finished = pyqtSignal()

    def __init__(self, parent, progress_bar, cancel_btn, network_manager):
        QObject.__init__(self, parent)
        self._progress = None
        self._network_manager = network_manager
        self._progress_bar = progress_bar
        self._cancel_btn = cancel_btn
        self._tmp = None
        self._req = None
        self._rep = None

    @classmethod
    def builder(cls, network_manager, **kwargs):
        def build(parent, progress_bar, cancel_btn):
            return cls(parent, progress_bar, cancel_btn, network_manager)
        return build

    def exec_(self, url):
        self._logger.info('Downloading {}'.format(url))
        self._setup_progress()
        self._prepare_download(url)

    def _prepare_download(self, url):
        self._logger.debug('_prepare_download')
        self._tmp = tempfile.NamedTemporaryFile(mode='w+b',
                                                suffix=".msi",
                                                delete=False)
        self._req = QNetworkRequest(QUrl(url))
        self._rep = self._network_manager.get(self._req)
        self._rep.setReadBufferSize(0)
        self._rep.downloadProgress.connect(self._on_progress)
        self._rep.finished.connect(self._on_finished)
        self._rep.error.connect(self.error)
        self._rep.readyRead.connect(self._buffer)
        self._rep.sslErrors.connect(self.ssl_error)

    def ssl_error(self, errors):
        estrings = [e.errorString() for e in errors]
        self._logger.error('ssl errors: {}'.format(estrings))
        self._rep.ignoreSslErrors()

    def error(self, code):
        self._logger.error(self._rep.errorString())

    def _buffer(self):
        self._tmp.write(self._rep.read(self._rep.bytesAvailable()))

    def _on_finished(self):
        self._logger.debug('_on_finished')
        assert self._tmp
        assert self._rep.atEnd()
        if self._rep.error() != QNetworkReply.NoError:
            self._logger.error(self._rep.errorString())
            return          # FIXME - handle

        self._tmp.close()

        redirected = self._rep.attribute(
            QNetworkRequest.RedirectionTargetAttribute)
        if redirected is not None:
            self._logger.debug('redirected to {}'.format(redirected))
            os.remove(self._tmp.name)
            if redirected.isRelative():
                url = self._rep.url().resolved(redirected)
            else:
                url = redirected
            self._prepare_download(url)
        else:
            self._run_installer()

    def _run_installer(self):
        command = 'msiexec /i "{msiname}" & del "{msiname}"'.format(
            msiname=self._tmp.name)
        self._logger.debug(r'Running msi installation command: ' + command)
        subprocess.Popen(command, shell=True)
        client.instance.close()

    def _on_progress(self, bytesReceived, bytesTotal):
        # only show for "real" download, i.e. bytesTotal > 5MB
        if (bytesTotal > 5*1024**2):
            self._progress_bar.setMaximum(bytesTotal)
            self._progress_bar.setValue(bytesReceived)

    def cancel(self):
        self._rep.abort()
        self.finished.emit()

    def _setup_progress(self):
        self._cancel_btn.show()
        self._progress_bar.show()
        self._progress_bar.setValue(0)
        self._cancel_btn.clicked.connect(self.cancel)
