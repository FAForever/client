from PyQt4 import QtCore, QtGui
import util
from friendlistdialog import FriendListDialog


class FriendList():

    def __init__(self, client):
        self.client = client

        util.settings.beginGroup("friendlist")
        self.enabled = util.settings.value('enabled', 'true') == 'true'
        self.client.actionFriendlist.blockSignals(True)
        self.client.actionFriendlist.setChecked(self.enabled)
        self.client.actionFriendlist.blockSignals(False)
        util.settings.endGroup()

        self.groups = [FriendGroup('online', client), FriendGroup('offline', client)]
        for i in xrange(len(self.groups)):
            self.groups[i].id = i

        self.dialog = FriendListDialog(self, client)
        self.users = set()

    def addUser(self, user):
        self.users.add(user)
        if self.client.isFriend(user):
            self.dialog.removeFriend(1, user)
            self.dialog.addFriend(0,user)

    def removeUser(self, user):
        # remove only users in friendlist
        if user not in self.users:
            return
        self.users.remove(user)
        if self.client.isFriend(user):
            self.dialog.removeFriend(0, user)
            self.dialog.addFriend(1, user)

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

    def getGroups(self):
        return self.groups

class FriendGroup():
    def __init__(self, name, client):
        self.name = name
        self.client = client
        self.users = []
        self.id = -1


    def getId(self):
        '''
        ID, initial used for sorting the groups
        '''
        return self.id

    def addUser(self, user):
        self.users.append(User(user, self))

    def getRowOfUser(self, user):
        for i in xrange(0, len(self.users)):
            if self.users[i].username == user:
                return i
        return -1

# cache for user information to speed up model
class User():
    indent = 6

    def __init__(self, username, group):
        self.username = username
        self.name = group.client.getCompleteUserName(username)
        self.group = group
        self.country = group.client.getUserCountry(username)
        self.rating = group.client.getUserRanking(username)
        # TOO: fix it ...  called before avatar is loaded
        self.avatarNotLoaded = False
        self.loadPixmap()


    def loadPixmap(self):
        self.pix = QtGui.QPixmap(40 + 16 + self.indent, 20)
        self.pix.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(self.pix)

        self.avatar = self.group.client.getUserAvatar(self.username)
        if  self.avatar:
            avatarPix = util.respix(self.avatar['url'])
            if avatarPix:
                painter.drawPixmap(0, 0, avatarPix)
                self.avatarNotLoaded = False
            else:
                self.avatarNotLoaded = True

        if self.country != None:
            painter.drawPixmap(40 + self.indent, 2, util.icon("chat/countries/%s.png" % self.country.lower(), pix=True))
        painter.end()

    def __str__(self):
        return self.username

    def __repr__(self):
        return self.username
