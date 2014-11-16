
from PyQt4 import QtGui
from chat._avatarWidget import avatarWidget


class Admin_Action():

    def __init__(self, client):
        self.client_window = client

    def addAvatar(self, username):
        avatarSelection = avatarWidget(self.client_window, username)
        avatarSelection.exec_()

    def joinChannel(self, username):
        channel, ok = QtGui.QInputDialog.getText(self.client_window, "QInputDialog.getText()", "Channel :", QtGui.QLineEdit.Normal, "#tournament")
        if ok and channel != '':
            self.client_window.joinChannel(username, channel)

    def kick(self):
        pass

    def closeFA(self, username):
        self.client_window.closeFA(username)

    def closeLobby(self, username):
        self.client_window.closeLobby(username)