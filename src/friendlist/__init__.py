from PyQt4 import QtCore, QtGui
from friendlist.friendlistdialog import FriendListDialog
import util



class FriendList():

    def __init__(self, client):
        self.client = client

        util.settings.beginGroup("friendlist")
        self.enabled = util.settings.value('enabled', 'true') == 'true'
        self.client.actionFriendlist.blockSignals(True)
        self.client.actionFriendlist.setChecked(self.enabled)
        self.client.actionFriendlist.blockSignals(False)
        util.settings.endGroup()

        self.dialog = FriendListDialog(client)
        self.users = set()

    def addUser(self, user):
        self.users.add(user)
        if self.client.isFriend(user):
            self.dialog.removeFriend(1, user)
            self.dialog.addFriend(0,user)

    def removeUser(self, user):
        if user in self.users:
            self.users.remove(user)
            if self.client.isFriend(user):
                self.dialog.removeFriend(0, user)
                self.dialog.addFriend(1, user)
        else:
            print 'not registered:', user

    def addFriend(self, friend):
        self.addUser(friend)

    def removeFriend(self, friend):
        self.dialog.removeFriend(0, friend)
        self.dialog.removeFriend(1, friend)


    def updateFriendList(self):
        for friend in self.client.friends:
            if friend in self.users:
                self.dialog.addFriend(0,friend)
            else:
                self.dialog.addFriend(1,friend)
