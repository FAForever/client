from PyQt4 import QtCore
import util
from notificatation_system.ns_hook import NsHook
import notificatation_system as ns


class NsHookNewGame(NsHook):
    def __init__(self):
        NsHook.__init__(self, ns.NotificationSystem.NEW_GAME)
        self.button.setEnabled(True)
        self.dialog = NewGameDialog(self, self.eventType)
        self.button.clicked.connect(self.dialog.show)

FormClass, BaseClass = util.loadUiType("notification_system/new_game.ui")
class NewGameDialog(FormClass, BaseClass):
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

        self.checkBoxFriends.setCheckState(QtCore.Qt.Checked if self.mode == 'friends' else QtCore.Qt.Unchecked)
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
        self.mode = 'friends' if self.checkBoxFriends.checkState() == QtCore.Qt.Checked else 'all'
        self.saveSettings()
        self.hide()