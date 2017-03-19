from PyQt5 import QtWidgets
import util
from config import Settings

"""
Setting Model class.
All Event Types (Notifications) are customizable.
Required are "popup, sound, enabled" settings.
You can add custom settings over the "settings" button.
connect on clicked event some actions, e.g.

self.button.clicked.connect(self.dialog.show)
"""
class NsHook():
    def __init__(self, eventType):
        self.eventType = eventType
        self._settings_key = 'notifications/{}'.format(eventType)
        self.loadSettings()
        self.button = QtWidgets.QPushButton('More')
        self.button.setEnabled(False)

    def loadSettings(self):
        self.popup = Settings.get(self._settings_key + '/popup',
                                  True, type=bool)
        self.sound = Settings.get(self._settings_key + '/sound',
                                  True, type=bool)

    def saveSettings(self):
        Settings.set(self._settings_key+'/popup', self.popup)
        Settings.set(self._settings_key+'/sound', self.sound)

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
