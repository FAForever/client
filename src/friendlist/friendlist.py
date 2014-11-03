from PyQt4 import QtCore, QtGui
import util

class FriendGroup():
    def __init__(self, name, client):
        self.client = client
        self.name = name
        self.users = []

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