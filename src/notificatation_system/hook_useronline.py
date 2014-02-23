from PyQt4 import QtCore, QtGui
import util
from notificatation_system.ns_hook import NsHook
import notificatation_system as ns


class NsHookUserOnline(NsHook):
    def __init__(self):
        NsHook.__init__(self, ns.NotificationSystem.USER_ONLINE)
        self.button.setEnabled(True)
        self.button.clicked.connect(self.pressMore)

    def pressMore(self):
        if not hasattr(self, 'dialog'):
            self.dialog = UserOnlineDialog(self.eventType)
        self.dialog.show()

FormClass, BaseClass = util.loadUiType("notification_system/user_online.ui")
class UserOnlineDialog(FormClass, BaseClass):
    def __init__(self, eventType):
        BaseClass.__init__(self)
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

    def saveSettings(self):
        util.settings.beginGroup("notification_system")
        util.settings.beginGroup(self.eventType)
        util.settings.setValue('mode', self.mode)
        util.settings.endGroup()
        util.settings.endGroup()
        util.settings.sync()

    @QtCore.pyqtSlot()
    def on_btnSave_clicked(self):
        self.mode = 'friends' if self.radioButtonFriends.isChecked() else 'all'
        self.saveSettings()
        self.hide()