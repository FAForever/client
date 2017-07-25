import tempfile
import client
import subprocess
import json
from semantic_version import Version
import config
import os
from config import Settings
import util

from client.update_settings import UpdateBranch, UpdateSettingsDialog

from decorators import with_logger
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QLabel, QLayout
from PyQt5.QtCore import QUrl, QObject
from PyQt5.QtNetwork import QNetworkRequest, QNetworkReply

class UpdateSettings:
    updater_branch = Settings.persisted_property('updater/branch', type=str, default_value=UpdateBranch.Prerelease.name)

    def should_notify(self, releases, force=True):
        have_server = 'server' in releases
        have_stable = 'stable' in releases
        have_pre = 'pre' in releases
        have_beta = 'beta' in releases

        if force:
            return have_server or have_stable or have_pre or have_beta
        else:
            current_version = Version(config.VERSION)
            # null out build because we don't care about it
            current_version.build = ()

            notify_stable = have_stable and self.updater_branch == UpdateBranch.Stable.name and Version(releases['stable']['new_version']) > current_version
            notify_pre = have_pre and self.updater_branch == UpdateBranch.Prerelease.name and Version(releases['pre']['new_version']) > current_version
            notify_beta = have_beta and self.updater_branch == UpdateBranch.Unstable.name and Version(releases['beta']['new_version']) > current_version

            return have_server or notify_stable or notify_pre or notify_beta

FormClass, BaseClass = util.THEME.loadUiType("client/update.ui")

@with_logger
class UpdateDialog(FormClass, BaseClass):
    changelog_url = Settings.persisted_property('updater/changelog_url', type=str, default_value='https://github.com/FAForever/client/releases/tag')

    def __init__(self, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self._logger.debug("UpdateDialog instantiating")
        self.setModal(True)

    def setup(self, releases):
        self.setupUi(self)

        self.btnStart.clicked.connect(self.startUpdate)
        self.btnAbort.clicked.connect(self.abort)
        self.btnSettings.clicked.connect(self.showSettings)

        self.cbReleases.currentIndexChanged.connect(self.indexChanged)

        self.layout().setSizeConstraint(QLayout.SetFixedSize);

        self.releases = releases
        self.reset_controls()

    def reset_controls(self):
        self.pbDownload.hide()
        self.btnCancel.hide()
        self.btnAbort.setEnabled(True)

        if 'server' in self.releases:
            self.lblUpdatesFound.setText('Your client version is outdated - you must update to play.')
        else:
            self.lblUpdatesFound.setText('Client updates were found.')

        if len(self.releases) > 0:
            currIdx = 0
            preferIdx = 0

            self.cbReleases.blockSignals(True)
            self.cbReleases.clear()
            for release_key in [('server', 'Server Version'), ('stable', 'Stable Version'), ('pre', 'Stable Prerelease'), ('beta', 'Unstable')]:
                key = release_key[0]
                label = release_key[1]
                if key in self.releases:
                    self._logger.debug(self.releases[key])
                    self.cbReleases.insertItem(99, '{} {}'.format(label, self.releases[key]['new_version']), self.releases[key])

                    branch_to_key = dict(Stable='stable', Prerelease='pre', Unstable='beta')

                    if key == branch_to_key[UpdateSettings().updater_branch]:
                        preferIdx = currIdx

                    currIdx = currIdx + 1

            self.cbReleases.setCurrentIndex(preferIdx)
            self.indexChanged(preferIdx)
            self.cbReleases.blockSignals(False)

            self.btnStart.setEnabled(True)

    @QtCore.pyqtSlot(int)
    def indexChanged(self, index):
        def _format_changelog(version):
            if version is not None:
                return "<a href=\"{}/{}\">Release Info</a>".format(self.changelog_url, version)
            else:
                return 'Not available'

        release = self.cbReleases.itemData(index)

        self.lblInfo.setText(_format_changelog(release['new_version']))

    def startUpdate(self):
        sender = self.sender()

        release = self.cbReleases.itemData(self.cbReleases.currentIndex())
        url = release['update']

        self.btnStart.setEnabled(False)
        self.btnAbort.setEnabled(False)

        client_updater = ClientUpdater(parent=self, progress_bar=self.pbDownload, cancel_btn=self.btnCancel)
        client_updater.finished.connect(self.finishUpdate)
        client_updater.exec_(url)

    def finishUpdate(self):
        self.reset_controls()

    def abort(self):
        self.close()

    def showSettings(self):
        dialog = UpdateSettingsDialog(self)
        dialog.setup()
        dialog.show()

@with_logger
class UpdateChecker(QObject):
    gh_releases_url = Settings.persisted_property('updater/gh_release_url', type=str, default_value='https://api.github.com/repos/FAForever/client/releases?per_page=20')

    # Signal that contains Unstable Release (from Github), Prerelease (from Github),
    # Stable Release (from Github) and Minimum Release (from Server)
    # dict members:
    #   new_version: version string
    #   update: url
    finished = QtCore.pyqtSignal(dict)

    def __init__(self, parent, respect_notify=True):
        QObject.__init__(self, parent)
        self._network_manager = client.NetworkManager
        self.respect_notify = respect_notify
        self._releases = None

    def start(self, reset_server=True):
        gh_url = QUrl(self.gh_releases_url)
        self._rep = self._network_manager.get(QNetworkRequest(gh_url))
        self._rep.finished.connect(self._req_done)
        if reset_server:
            self._server_info = None

    def server_update(self, message):
        self._server_info = message
        self._check_updates_complete()

    def server_session(self):
        self._server_info = {}
        self._check_updates_complete()

    def _parse_releases(self, release_info):
        def _parse_release(release_dict):
            for asset in release_dict['assets']:
                if '.msi' in asset['browser_download_url']:
                    download_url = asset['browser_download_url']
                    tag = release_dict['tag_name']
                    return dict(
                            update=download_url,
                            new_version=tag)
        try:
            releases = json.loads(release_info.decode('utf-8'))
            if not isinstance(releases, list):
                releases = [releases]
            self._logger.debug('Loaded {} github releases'.format(len(releases)))

            beta = None
            stable = None
            pre = None

            for release in releases:
                tag = release.get('tag_name')
                release_version = Version(tag)
                if beta is None:
                    # odd minor version = unstable branch
                    if release_version.minor % 2 == 1:
                        beta = _parse_release(release)
                elif stable is None:
                    # even minor version = stable branch
                    if release_version.minor % 2 == 0 and release_version.prerelease == ():
                        stable = _parse_release(release)
                elif pre is None:
                    if release_version.minor % 2 == 0 and release_version.prerelease != ():
                        pre = _parse_release(release)
                else:
                    break

            return dict(
                    beta=beta,
                    stable=stable,
                    pre=pre)
        except:
            self._logger.exception("Error parsing network reply: {}".format(repr(release_info)))
            return dict()

    def _req_done(self):
        if self._rep.error() == QNetworkReply.NoError:
            self._releases = self._parse_releases(bytes(self._rep.readAll()))
        else:
            self._releases = {}

        self._check_updates_complete()

    def _check_updates_complete(self):
        if self._server_info is not None and self._releases is not None:
            releases = self._releases
            if self._server_info != {}:
                releases['server'] = self._server_info
            if UpdateSettings().should_notify(releases, force = not self.respect_notify):
                self.finished.emit(releases)



@with_logger
class ClientUpdater(QObject):

    finished = QtCore.pyqtSignal()

    def __init__(self, parent, progress_bar, cancel_btn):
        QObject.__init__(self, parent)
        self._progress = None
        self._network_manager = client.NetworkManager
        self._progress_bar = progress_bar
        self._cancel_btn = cancel_btn
        self._tmp = None
        self._req = None
        self._rep = None

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

        redirected = self._rep.attribute(QNetworkRequest.RedirectionTargetAttribute)
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
        command = 'msiexec /i "{msiname}" & del "{msiname}"'.format(msiname=self._tmp.name)
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
