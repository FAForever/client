from PyQt5 import QtCore
import util
import config
from config import Settings
from notifications.ns_hook import NsHook
import notifications as ns

"""
Settings for notifications: if a player comes online
"""
class NsHookUserOnline(NsHook):
    def __init__(self):
        NsHook.__init__(self, ns.Notifications.USER_ONLINE)
        self.button.setEnabled(True)
        self.dialog = UserOnlineDialog(self, self.eventType)
        self.button.clicked.connect(self.dialog.show)

FormClass, BaseClass = util.loadUiType("notification_system/user_online.ui")
class UserOnlineDialog(FormClass, BaseClass):
    def __init__(self, parent, eventType):
        BaseClass.__init__(self)
        self.parent = parent
        self.eventType = eventType
        self._settings_key = 'notifications/{}'.format(eventType)
        self.setupUi(self)

        # remove help button
        self.setWindowFlags(self.windowFlags() & (~QtCore.Qt.WindowContextHelpButtonHint))

        self.loadSettings()


    def loadSettings(self):
        self.mode = Settings.get(self._settings_key+'/mode', 'friends')

        if self.mode == 'friends':
            self.radioButtonFriends.setChecked(True)
        else:
            self.radioButtonAll.setChecked(True)
        self.parent.mode = self.mode

    def saveSettings(self):
        Settings.set(self._settings_key+'/mode', self.mode)
        self.parent.mode = self.mode

    @QtCore.pyqtSlot()
    def on_btnSave_clicked(self):
        self.mode = 'friends' if self.radioButtonFriends.isChecked() else 'all'
        self.saveSettings()
        self.hide()
