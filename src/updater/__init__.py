from updater.base import UpdateSettings, UpdateChecker, UpdateNotifier
from updater.widgets import UpdateDialog, UpdateSettingsDialog
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QDialog, QMessageBox
from semantic_version import Version

class ClientUpdateTools(QObject):
    mandatory_update_aborted = pyqtSignal()

    def __init__(self, update_settings, checker, notifier, dialog,
                 parent_widget):
        QObject.__init__(self)
        self.update_settings = update_settings
        self.checker = checker
        self.notifier = notifier
        self.dialog = dialog
        self.parent_widget = parent_widget
        self.notifier.update.connect(self._handle_update)

    @classmethod
    def build(cls, current_version, parent_widget, network_manager,
              lobby_info):
        current_version = Version(current_version)
        update_settings = UpdateSettings()
        checker = UpdateChecker.build(current_version=current_version,
                                      lobby_info=lobby_info,
                                      settings=update_settings,
                                      network_manager=network_manager)
        notifier = UpdateNotifier(update_settings, checker)
        dialog = UpdateDialog.build(update_settings, parent_widget, current_version,
                                    network_manager=network_manager)
        return cls(update_settings, checker, notifier, dialog, parent_widget)

    def _handle_update(self, releases, mandatory):
        branch = self.update_settings.updater_branch.to_reltype()
        versions = releases.versions(branch,
                                     self.update_settings.updater_downgrade)
        if not versions:
            QMessageBox.information(self.parent_widget, "No updates found",
                                    "No client updates were found.")
            return
        self.dialog.setup(releases)
        result = self.dialog.exec_()
        if result == QDialog.Rejected and mandatory:
            self.mandatory_update_aborted.emit()

    def settings_dialog(self):
        return UpdateSettingsDialog(self.parent_widget, self.update_settings)
