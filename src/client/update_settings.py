import util
from config import Settings
from enum import Enum
from decorators import with_logger


class UpdateBranch(Enum):
    Stable = 0
    Prerelease = 1
    Unstable = 2

FormClass, BaseClass = util.THEME.loadUiType("client/update_settings.ui")


@with_logger
class UpdateSettingsDialog(FormClass, BaseClass):
    updater_branch = Settings.persisted_property('updater/branch', type=str, default_value=UpdateBranch.Prerelease.name)
    updater_downgrade = Settings.persisted_property('updater/downgrade', type=bool, default_value=False)

    def __init__(self, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setModal(True)

    def setup(self):
        self.setupUi(self)

        self.cbChannel.setCurrentIndex(UpdateBranch[self.updater_branch].value)
        self.cbDowngrade.setChecked(self.updater_downgrade)

        self.buttonBox.accepted.connect(self.accepted)
        self.buttonBox.rejected.connect(lambda: self.close())

    def accepted(self):
        branch = UpdateBranch(self.cbChannel.currentIndex())
        self.updater_branch = branch.name
        self.updater_downgrade = self.cbDowngrade.isChecked()
        self.close()
