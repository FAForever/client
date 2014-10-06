from PyQt4 import QtCore
import util
from notificatation_system.ns_hook import NsHook
import notificatation_system as ns

"""
Settings for notifications: if a player comes online
"""
class NsHookUserOnline(NsHook):
    def __init__(self):
        NsHook.__init__(self, ns.NotificationSystem.USER_ONLINE)
        self.button.setEnabled(True)
        self.dialog = UserOnlineDialog(self, self.eventType)
        self.button.clicked.connect(self.dialog.show)

FormClass, BaseClass = util.loadUiType("notification_system/user_online.ui")
class UserOnlineDialog(FormClass, BaseClass):
    def __init__(self, parent, eventType):
        BaseClass.__init__(self)
        self.parent = parent
        self.eventType = eventType
        self.setupUi(self)

        # remove help button
        self.setWindowFlags(self.windowFlags() & (~QtCore.Qt.WindowContextHelpButtonHint))

        self.loadSettings()


    def loadSettings(self):
        util.settings.beginGroup("notification_system")
        util.settings.beginGroup(self.eventType)
        self.mode = util.settings.value('mode', 'friends')
        util.settings.endGroup()
        util.settings.endGroup()

        if self.mode == 'friends':
            self.radioButtonFriends.setChecked(True)
        else:
            self.radioButtonAll.setChecked(True)
        self.parent.mode = self.mode

    def saveSettings(self):
        util.settings.beginGroup("notification_system")
        util.settings.beginGroup(self.eventType)
        util.settings.setValue('mode', self.mode)
        util.settings.endGroup()
        util.settings.endGroup()
        util.settings.sync()
        self.parent.mode = self.mode

    @QtCore.pyqtSlot()
    def on_btnSave_clicked(self):
        self.mode = 'friends' if self.radioButtonFriends.isChecked() else 'all'
        self.saveSettings()
        self.hide()