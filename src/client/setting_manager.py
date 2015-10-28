from PyQt4 import QtCore
from client import GAME_PORT_DEFAULT # This import is the wrong way around, we should fix this
import util

class SettingManager(QtCore.QObject):
    """
    Interface to Load and Store client relevant settings.
    """
    def __init__(self, client):
        self.client = client

    def saveCredentials(self):
        util.settings.beginGroup("user")
        util.settings.setValue("user/remember", self.client.remember) # always remember to remember
        if self.client.remember:
            util.settings.setValue("user/login", self.client.login)
            util.settings.setValue("user/password", self.client.password)
            util.settings.setValue("user/autologin", self.client.autologin) # only autologin if remembering
        else:
            util.settings.setValue("user/login", None)
            util.settings.setValue("user/password", None)
            util.settings.setValue("user/autologin", False)
        util.settings.endGroup()
        util.settings.sync()


    def clearAutologin(self):
        self.client.autologin = False
        self.client.actionSetAutoLogin.setChecked(False)

        util.settings.beginGroup("user")
        util.settings.setValue("user/autologin", False)
        util.settings.endGroup()
        util.settings.sync()

    def saveWindow(self):
        util.settings.beginGroup("window")
        util.settings.setValue("geometry", self.client.saveGeometry())
        util.settings.endGroup()
        util.settings.beginGroup("ForgedAlliance")
        util.settings.setValue("app/falogs", self.client.gamelogs)
        util.settings.endGroup()

    def savePort(self):
        util.settings.beginGroup("ForgedAlliance")
        util.settings.setValue("app/gameport", self.client.gamePort)
        util.settings.setValue("app/upnp", self.client.useUPnP)

        util.settings.endGroup()
        util.settings.sync()

    def saveMumble(self):
        util.settings.beginGroup("Mumble")
        util.settings.setValue("app/mumble", self.client.enableMumble)
        util.settings.endGroup()
        util.settings.sync()

    @QtCore.pyqtSlot()
    def saveMumbleSwitching(self):
        self.client.activateMumbleSwitching = self.client.actionActivateMumbleSwitching.isChecked()

        util.settings.beginGroup("Mumble")
        util.settings.setValue("app/activateMumbleSwitching", self.client.activateMumbleSwitching)
        util.settings.endGroup()
        util.settings.sync()

    def saveChat(self):
        util.settings.beginGroup("chat")
        util.settings.setValue("soundeffects", self.client.soundeffects)
        util.settings.setValue("livereplays", self.client.livereplays)
        util.settings.setValue("opengames", self.client.opengames)
        util.settings.setValue("joinsparts", self.client.joinsparts)
        util.settings.setValue("coloredNicknames", self.client.coloredNicknames)
        util.settings.endGroup()

    @QtCore.pyqtSlot()
    def clearSettings(self):
        result = QtGui.QMessageBox.question(self.client,
                                            "Clear Settings",
                                            "Are you sure you wish to clear all settings, login info, etc. used by this program?",
                                            QtGui.QMessageBox.Yes,
                                            QtGui.QMessageBox.No)
        if (result == QtGui.QMessageBox.Yes):
            util.settings.clear()
            util.settings.sync()
            QtGui.QMessageBox.information(self.client, "Restart Needed", "FAF will quit now.")
            QtGui.QApplication.quit()

    def loadSettingsPrelogin(self):
        util.settings.beginGroup("user")
        self.client.login = util.settings.value("user/login")
        self.client.password = util.settings.value("user/password")
        self.client.remember = (util.settings.value("user/remember") == "true")

        # This is the new way we do things.
        self.client.autologin = (util.settings.value("user/autologin") == "true")
        self.client.actionSetAutoLogin.setChecked(self.client.autologin)
        util.settings.endGroup()

    def loadSettings(self):
        util.settings.beginGroup("window")
        geometry = util.settings.value("geometry", None)
        if geometry:
            self.client.restoreGeometry(geometry)
        util.settings.endGroup()

        util.settings.beginGroup("ForgedAlliance")
        self.client.gamePort = int(util.settings.value("app/gameport", GAME_PORT_DEFAULT))
        self.client.useUPnP = (util.settings.value("app/upnp", "false") == "true")
        self.client.gamelogs = (util.settings.value("app/falogs", "false") == "true")
        self.client.actionSaveGamelogs.setChecked(self.client.gamelogs)
        util.settings.endGroup()

        util.settings.beginGroup("Mumble")

        if util.settings.value("app/mumble", "firsttime") == "firsttime":
            # The user has never configured mumble before. Be a little intrusive and ask him if he wants to use it.
            if QtGui.QMessageBox.question(self.client,
                                          "Enable Voice Connector?",
                                          'FA Forever can connect with <a href="http://mumble.sourceforge.net/">Mumble</a> to support the automatic setup of voice connections between you and your team mates. Would you like to enable this feature? You can change the setting at any time by going to options -> settings -> Voice',
                                          QtGui.QMessageBox.Yes,
                                          QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
                util.settings.setValue("app/mumble", "true")
            else:
                util.settings.setValue("app/mumble", "false")

        if util.settings.value("app/activateMumbleSwitching", "firsttime") == "firsttime":
            util.settings.setValue("app/activateMumbleSwitching", "true")

        self.client.enableMumble = (util.settings.value("app/mumble", "false") == "true")
        self.client.activateMumbleSwitching = (util.settings.value("app/activateMumbleSwitching", "false") == "true")
        util.settings.endGroup()

        self.client.actionActivateMumbleSwitching.setChecked(self.client.activateMumbleSwitching)

        self.client.loadChat()
