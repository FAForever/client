import tempfile
import client
import subprocess
import json
from semantic_version import Version
import config
import os
from config import Settings

from decorators import with_logger
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QUrl, QObject
from PyQt5.QtNetwork import QNetworkRequest, QNetworkReply


@with_logger
class GithubUpdateChecker(QObject):
    gh_release_url = Settings.persisted_property('updater/gh_release_url', type=str, default_value='https://api.github.com/repos/FAForever/client/releases?per_page=1')

    update_found = QtCore.pyqtSignal(dict)

    def __init__(self):
        QObject.__init__(self)
        self._network_manager = client.NetworkManager

    def start(self):
        url = QUrl(self.gh_release_url)
        self._rep = self._network_manager.get(QNetworkRequest(url))
        self._rep.finished.connect(self._req_done)

    def _req_done(self):
        try:
            body = self._rep.readAll()
            js = json.loads(bytes(body).decode('utf-8'))[0]
            tag = js.get('tag_name')
            self._logger.info('Found release on github: {}'.format(js.get('name')))
            if tag is not None:
                curr_ver = config.VERSION.split('-')[0]
                if Version(tag) > Version(curr_ver):
                    self._logger.info('Should update {} -> {}'.format(curr_ver, tag))
                    self.update_found.emit(js)
        except:
            self._logger.exception("Error parsing network reply")


@with_logger
class ClientUpdater(QObject):
    def __init__(self):
        QObject.__init__(self)
        self._progress = None
        self._network_manager = client.NetworkManager
        self._tmp = None
        self._req = None
        self._rep = None
        # Info needed for update comes from 2 sources - github and server
        # We need server to tell us whether we're outdated before we update
        self._outdated = None
        self._postponed_exec = None

    def notify_outdated(self, outdated):
        self._outdated = outdated
        if self._postponed_exec is not None:
            call = self._postponed_exec
            self._postponed_exec = None
            call()

    def exec_(self, url, is_pre=False, info_url='https://github.com/FAForever/client/blob/develop/changelog.md'):
        if self._outdated is None:
            # Postpone the update until we know if we're outdated
            self._postponed_exec = lambda: self.exec_(url, is_pre, info_url)
            return

        update_msg = {
                True: (
                    "Update needed",
                    "Your version of FAF is outdated. You need to download and install the most recent version to connect and play.<br/><br/><b>Do you want to download and install the update now?</b><br/><br/><a href='{}'>See changes</a>".format(info_url)
                    ),
                False: (
                    "Update available",
                    "There is a new{} version of FAF.<br/><b>Would you like to download and install this update now?</b><br/><br/><a href='{}'>See information</a>".format(
                        ' beta' if is_pre else ' release',
                        info_url
                        )
                    )
                }
        result = QtWidgets.QMessageBox.question(None,
                                            update_msg[self._outdated][0],
                                            update_msg[self._outdated][1],
                                            QtWidgets.QMessageBox.No,
                                            QtWidgets.QMessageBox.Yes)
        if result == QtWidgets.QMessageBox.Yes:
            self._logger.info('Downloading {}'.format(url))
            self._setup_progress()
            self._prepare_download(url)
            self._progress.show()
        elif self._outdated:
            QtWidgets.QApplication.quit()

    def _prepare_download(self, url):
        self._tmp = tempfile.NamedTemporaryFile(mode='w+b',
                                                suffix=".msi",
                                                delete=False)
        self._req = QNetworkRequest(QUrl(url))
        self._rep = self._network_manager.get(self._req)
        self._rep.setReadBufferSize(0)
        self._rep.downloadProgress.connect(self.on_progress)
        self._rep.finished.connect(self._on_finished)
        self._rep.error.connect(self.error)
        self._rep.readyRead.connect(self._buffer)


    def error(self, code):
        self._logger.exception(self._rep.errorString())

    def _buffer(self):
        self._tmp.write(self._rep.read(self._rep.bytesAvailable()))

    def _on_finished(self):
        assert self._tmp
        assert self._rep.atEnd()
        if self._rep.error() != QNetworkReply.NoError:
            return          # FIXME - handle

        self._tmp.close()

        redirected = self._rep.attribute(QNetworkRequest.RedirectionTargetAttribute)
        if redirected is not None:
            os.remove(self._tmp.name)
            if redirected.isRelative():
                url = self._rep.url().resolved(redirected)
            else:
                url = redirected
            self._prepare_download(url)
        else:
            self._run_installer()

    def _run_installer(self):
        command = 'msiexec /i "{msiname}" & del "{msiname}"'.format(msiname=self._tmp.name)
        self._logger.debug(r'Running msi installation command: ' + command)
        subprocess.Popen(command, shell=True)
        self._progress.close()

    def on_progress(self, current, max):
        self._progress.setMaximum(max)
        self._progress.setValue(current)

    def cancel(self):
        self._rep.abort()
        QtWidgets.QApplication.quit()

    def _setup_progress(self):
        progress = QtWidgets.QProgressDialog()
        progress.setMinimumDuration(0)
        progress.setLabel(QLabel("Downloading update"))
        progress.setCancelButtonText("Cancel")
        progress.canceled.connect(self.cancel)
        progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint
                                | QtCore.Qt.WindowTitleHint)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setAutoClose(True)
        progress.setAutoReset(False)
        self._progress = progress
