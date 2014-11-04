from PyQt4 import QtCore, QtGui
import util

class FriendList(QtCore.QObject):
    ONLINE = 0
    OFFLINE = 1

    remove_user =  QtCore.pyqtSignal(object, object) # group, user
    add_user =  QtCore.pyqtSignal(object, object) # group, user

    def __init__(self, api):
        super(FriendList, self).__init__()
        self.api = api

        self.groups = [FriendGroup('online', self), FriendGroup('offline', self)]
        for i in xrange(len(self.groups)):
            self.groups[i].id = i

        self.users = set()

        self.api.usersUpdated.connect(self.updateUser)

    def updateUser(self, updatedUsers):
        for user in updatedUsers:
            if user not in self.users:
                continue
            self.dialog.updateGameStatus(user)

    def addUser(self, user):
        if not self.api.isFriend(user) or user in self.users:
            return

        self.users.add(user)
        self.remove_user.emit(self.OFFLINE, user)
        self.add_user.emit(self.ONLINE, user)

    def removeUser(self, user):
        # remove only users in friendlist
        if user not in self.users:
            return
        self.users.remove(user)
        if self.api.isFriend(user):
            self.remove_user.emit(self.ONLINE, user)
            self.add_user.emit(self.OFFLINE, user)

    def addFriend(self, friend):
        self.addUser(friend)

    def removeFriend(self, friend):
        if friend not in self.users:
            return
        self.users.remove(friend)
        self.remove_user.emit(self.ONLINE, friend)
        self.remove_user.emit(self.OFFLINE, friend)


    def updateFriendList(self):
        for friend in self.api.getFriends():
            if friend in self.users:
                self.dialog.addFriend(self.ONLINE, friend)
            else:
                self.dialog.addFriend(self.OFFLINE, friend)

    def getGroups(self):
        return self.groups

class FriendGroup():
    def __init__(self, name, friendlist):
        self.name = name
        self.friendlist = friendlist
        self.api = friendlist.api
        self.users = []
        self.id = -1


    def getId(self):
        '''
        ID, initial used for sorting the groups
        '''
        return self.id

    def addUser(self, user):
        self.users.append(User(user, self))

    # TODO: increase performance
    def getRowOfUser(self, username):
        for i in xrange(0, len(self.users)):
            if self.users[i].username == username:
                return i
        return -1

    # TODO: increase performance
    def getUser(self, username):
        for i in xrange(0, len(self.users)):
            if self.users[i].username == username:
                return self.users[i]
        return None

# cache for user information to speed up model
class User():
    indent = 6

    def __init__(self, username, group):
        self.username = username
        self.name = group.api.getCompleteUserName(username)
        self.group = group
        self.country = group.api.getUserCountry(username)
        self.rating = group.api.getUserRanking(username)
        # TOO: fix it ...  called before avatar is loaded
        self.avatarNotLoaded = False
        self.loadPixmap()


    def loadPixmap(self):
        self.pix = QtGui.QPixmap(40 + 16 + self.indent, 20)
        self.pix.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(self.pix)

        self.avatar = self.group.api.getUserAvatar(self.username)
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
