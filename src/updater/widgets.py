import util
from updater.base import UpdateChannel, VersionBranch
from updater.process import ClientUpdater
from decorators import with_logger
from PyQt5.QtWidgets import QLayout


FormClass, BaseClass = util.THEME.loadUiType("client/update.ui")


@with_logger
class UpdateDialog(FormClass, BaseClass):
    def __init__(self, settings, parent_widget, current_version,
                 updater_builder):
        BaseClass.__init__(self, parent_widget)
        self._settings = settings
        self._current_version = current_version
        self._updater_builder = updater_builder
        self.setModal(True)
        self.setupUi(self)
        self.btnStart.clicked.connect(self.startUpdate)
        self.btnAbort.clicked.connect(self.abort)
        self.btnSettings.clicked.connect(self.showSettings)
        self.cbReleases.currentIndexChanged.connect(self.indexChanged)
        self.layout().setSizeConstraint(QLayout.SetFixedSize)

    @classmethod
    def build(cls, settings, parent_widget, current_version, **kwargs):
        updater_builder = ClientUpdater.builder(**kwargs)
        return cls(settings, parent_widget, current_version, updater_builder)

    def setup(self, releases):
        self._releases = releases
        self.reset_controls()

    def reset_controls(self):
        self.pbDownload.hide()
        self.btnCancel.hide()
        self.btnAbort.setEnabled(True)

        branch = self._settings.updater_branch.to_version()
        if self._releases.mandatory_update():
            text = 'Your client version is outdated - you must update to play.'
        elif self._releases.optional_update(branch):
            text = 'Client updates were found.'
        else:
            text = 'Client releases were found.'
        self.lblUpdatesFound.setText(text)

        versions = self._releases.versions(branch,
                                           self._settings.updater_downgrade)
        newest_version = self._releases.newest(branch)

        labels = {
            VersionBranch.MINIMUM: 'Server Version',
            VersionBranch.STABLE: 'Stable Version',
            VersionBranch.PRERELEASE: 'Stable Prerelease',
            VersionBranch.UNSTABLE: 'Unstable'
        }

        self.cbReleases.blockSignals(True)
        self.cbReleases.clear()
        for rel in versions:
            new = ' [New!]' if rel.version > self._current_version else ''
            name = '{} {}{}'.format(labels[rel.branch], rel.version, new)
            self.cbReleases.addItem(name, rel)
        preferred_idx = self.cbReleases.findData(newest_version)
        if preferred_idx != -1:
            self.cbReleases.setCurrentIndex(preferred_idx)
            self.indexChanged(preferred_idx)
        self.cbReleases.blockSignals(False)

        if len(versions) > 0:
            self.btnStart.setEnabled(True)

    def indexChanged(self, index):
        release = self.cbReleases.itemData(index)
        self.lblInfo.setText(self._format_changelog(release.version))

    def _format_changelog(self, version):
        if version is not None:
            return "<a href=\"{}/{}\">Release Info</a>".format(
                self._settings.changelog_url, version)
        else:
            return 'Not available'

    def startUpdate(self):
        release = self.cbReleases.itemData(self.cbReleases.currentIndex())
        url = release.installer
        self.btnStart.setEnabled(False)
        self.btnAbort.setEnabled(False)
        client_updater = self._updater_builder(
            parent=self, progress_bar=self.pbDownload,
            cancel_btn=self.btnCancel)
        client_updater.finished.connect(self.finishUpdate)
        client_updater.exec_(url)

    def finishUpdate(self):
        self.reset_controls()

    def abort(self):
        self.close()

    def showSettings(self):
        dialog = UpdateSettingsDialog(self, self._settings)
        dialog.finished.connect(self.reset_controls)
        dialog.show()


FormClass, BaseClass = util.THEME.loadUiType("client/update_settings.ui")


@with_logger
class UpdateSettingsDialog(FormClass, BaseClass):
    def __init__(self, parent_widget, settings):
        BaseClass.__init__(self, parent_widget)
        self._settings = settings
        self.setModal(True)
        self.setupUi(self)
        self.cbChannel.setCurrentIndex(self._settings.updater_branch.value)
        self.cbDowngrade.setChecked(self._settings.updater_downgrade)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(lambda: self.close())

    def accept(self):
        branch = UpdateChannel(self.cbChannel.currentIndex())
        self._settings.updater_branch = branch
        self._settings.updater_downgrade = self.cbDowngrade.isChecked()
        super().accept()
