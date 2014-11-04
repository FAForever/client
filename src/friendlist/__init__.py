from PyQt4 import QtCore, QtGui
import util, logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class FriendList(QtCore.QObject):
    ONLINE = 0
    OFFLINE = 1

    remove_user = QtCore.pyqtSignal(object, str) # group, user
    add_user = QtCore.pyqtSignal(object, str) # group, user
    update_user = QtCore.pyqtSignal(str) # group, user

    def __init__(self, api):
        super(FriendList, self).__init__()
        self.api = api
        self.groups = [FriendGroup('online', self), FriendGroup('offline', self)]
        for i in xrange(len(self.groups)):
            self.groups[i].id = i
        self.api.usersUpdated.connect(self.updateUsers)

    def updateUsers(self, updatedUsers):
        for user in updatedUsers:
            self.updateUser(user)

    def updateUser(self, user):
        for group in self.groups:
            if not group.hasUser(user):
                continue
            self.update_user.emit(user)

    def switchUser(self, user, newStatus):
        if not self.api.isFriend(user) or self.groups[newStatus].hasUser(user):
            return
        self.removeUser(user)
        self.add_user.emit(newStatus, user)

    def removeUser(self, friend):
        for group in self.groups:
            if not group.hasUser(friend):
                continue
            self.remove_user.emit(group.id, friend)

    # called only once
    def updateFriendList(self):
        logger.debug("updateFriendList")
        for friend in self.api.getFriends():
            self.add_user.emit(self.OFFLINE, friend)

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

    def addUser(self, username, autoload = True):
        self.users.append(User(username, self, autoload))

    def removeUser(self, username):
        del self.users[self.getRowOfUser(username)]

    def hasUser(self, username):
        for group_user in self.users:
            if group_user.username == username:
                return True
        return False

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

    def __init__(self, username, group, autoload = True):
        self.username = username
        self.name = group.api.getCompleteUserName(username)
        self.group = group
        self.country = group.api.getUserCountry(username)
        self.rating = group.api.getUserRanking(username)
        # TOO: fix it ...  called before avatar is loaded
        self.avatarNotLoaded = False
        # for testing
        if autoload:
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
