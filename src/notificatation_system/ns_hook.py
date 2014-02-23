from PyQt4 import QtGui
import util


class NsHook():
    def __init__(self, eventType):
        self.eventType = eventType
        self.loadSettings()
        self.button = QtGui.QPushButton('More')
        self.button.setEnabled(False)

    def loadSettings(self):
        util.settings.beginGroup("notification_system")
        util.settings.beginGroup(self.eventType)
        self.popup = util.settings.value('popup', 'true') == 'true'
        self.sound = util.settings.value('sound', 'true') == 'true'
        util.settings.endGroup()
        util.settings.endGroup()

    def saveSettings(self):
        util.settings.beginGroup("notification_system")
        util.settings.beginGroup(self.eventType)
        util.settings.setValue('popup', self.popup)
        util.settings.setValue('sound', self.sound)
        util.settings.endGroup()
        util.settings.endGroup()
        util.settings.sync()

    def getEventDisplayName(self):
        return self.eventType

    def popupEnabled(self):
        return self.popup

    def switchPopup(self):
        self.popup = not self.popup
        self.saveSettings()

    def soundEnabled(self):
        return self.sound

    def switchSound(self):
        self.sound = not self.sound
        self.saveSettings()

    def settings(self):
        return self.button