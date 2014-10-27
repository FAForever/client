from PyQt4 import QtCore, QtGui
import util
from friendlist.ModelTest import ModelTest

FormClass, BaseClass = util.loadUiType("friendlist/friendlist.ui")
class FriendListDialog(FormClass, BaseClass):
    def __init__(self, client):
        BaseClass.__init__(self, client)
        self.client = client

        self.setupUi(self)

        self.updateTopLabel()

        self.model = FriendListModel([FriendGroup('online', client), FriendGroup('offline', client)], client)

        self.proxy = QtGui.QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(QtCore.Qt.UserRole)
        self.friendlist.setModel(self.proxy)

        self.friendlist.header().setStretchLastSection(False);
        self.friendlist.header().resizeSection (1, 48)
        self.friendlist.header().resizeSection (2, 64)
        self.friendlist.header().resizeSection (3, 18)

        # stretch first column
        self.friendlist.header().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.friendlist.expandAll()

        # remove Whats this button
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        # Frameless
        # self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowMinimizeButtonHint)

        # later use rubberband
        self.rubberBand = QtGui.QRubberBand(QtGui.QRubberBand.Rectangle)

        self.loadSettings()

        # detect if main window is closed
        self.closing = False
        self.client.closing_ui.connect(self.set_closing)

    def set_closing(self):
        self.closing = True

    def isClosing(self):
        return self.closing

    def updateTopLabel(self):
        self.labelUsername.setText(self.client.getCompleteUserName(self.client.login))

    def closeEvent(self, event):
        # if not a natural closing event, hide it
        # otherwise friendlist is always disabled
        if not self.isClosing():
            self.client.actionFriendlist.setChecked(False)

        self.saveSettings()
        event.accept()

    def loadSettings(self):
        util.settings.beginGroup("friendlist")
        x = util.settings.value('x', 0)
        y = util.settings.value('y', 0)
        width = util.settings.value('width', 334)
        height = util.settings.value('height', 291)
        util.settings.endGroup()
        self.setGeometry(QtCore.QRect(x, y, width, height))

    def saveSettings(self):
        util.settings.beginGroup("friendlist")
        geometry = self.geometry()
        util.settings.setValue('x', geometry.x())
        util.settings.setValue('y', geometry.y())
        util.settings.setValue('width', geometry.width())
        util.settings.setValue('height', geometry.height())
        util.settings.endGroup()
        util.settings.sync()

    def addFriend(self, groupIndex, username):
        '''
        groupIndex: 0 = online, 1 = offline
        '''
        self.updateTopLabel()
        n = len(self.model.root[groupIndex].users)
        self.model.beginInsertRows(self.model.index(groupIndex, 0, QtCore.QModelIndex()), n, n)
        self.model.root[groupIndex].addUser(username)
        self.model.endInsertRows()

    def removeFriend(self, groupIndex, username):
        row = self.model.root[groupIndex].getRowOfUser(username)
        if row > 0:
            self.model.beginRemoveRows(self.model.index(groupIndex, 0, QtCore.QModelIndex()), row, row)
            del self.model.root[groupIndex].users[row]
            self.model.endRemoveRows()

    @QtCore.pyqtSlot(QtCore.QPoint)
    def on_friendlist_customContextMenuRequested(self, pos):

        modelIndex = self.friendlist.indexAt(pos)
        if modelIndex == None or not modelIndex.isValid():
            return
        pointer = self.proxy.mapToSource(modelIndex).internalPointer()
        if pointer == None:
            return
        playername = pointer.username

        menu = QtGui.QMenu(self)

        # Actions for stats
        actionStats = QtGui.QAction("View Player statistics", menu)

        # Actions for Games and Replays
        actionReplay = QtGui.QAction("View Live Replay", menu)
        actionVaultReplay = QtGui.QAction("View Replays in Vault", menu)
        actionJoin = QtGui.QAction("Join in Game", menu)

        # Default is all disabled, we figure out what we can do after this
        actionReplay.setDisabled(True)
        actionJoin.setDisabled(True)

        # Triggers
        actionStats.triggered.connect(lambda : self.viewStats(playername))
        # actionReplay.triggered.connect(self.viewReplay)
        actionVaultReplay.triggered.connect(lambda : self.viewVaultReplay(playername))
        # actionJoin.triggered.connect(self.joinInGame)

        # Adding to menu
        menu.addAction(actionStats)

        menu.addSeparator()
        menu.addAction(actionReplay)
        menu.addAction(actionVaultReplay)
        menu.addSeparator()
        menu.addAction(actionJoin)

        # Actions for the Friends List
        actionRemFriend = QtGui.QAction("Remove friend", menu)

        # Don't allow self to be added or removed from friends or foes
        if self.client.login == playername:
            actionRemFriend.setDisabled(1)

        # Triggers
        actionRemFriend.triggered.connect(lambda : self.client.remFriend(playername))

        # Adding to menu
        menu.addSeparator()
        menu.addAction(actionRemFriend)

        # Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())

    def viewStats(self, username):
        try:
            if username in self.client.players :
                self.client.profile.setplayer(username)
                self.client.profile.show()
        except:
            pass

    def viewVaultReplay(self, username):
        ''' see the player replays in the vault '''
        self.client.replays.mapName.setText("")
        self.client.replays.playerName.setText(username)
        self.client.replays.minRating.setValue(0)
        self.client.replays.searchVault()
        self.client.mainTabs.setCurrentIndex(self.client.mainTabs.indexOf(self.client.replaysTab))


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


class FriendListModel(QtCore.QAbstractItemModel):
    def __init__(self, groups, client):
        QtCore.QAbstractItemModel.__init__(self)
        self.root = groups
        self.client = client

        self.header = ['Player', 'Land', 'Rating', '#']

    def columnCount(self, parent):
        return len(self.header);

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.header[col]
        return None

    def rowCount(self, parentIndex):
        pointer = parentIndex.internalPointer()
        # if root level
        if pointer is None:
            return len(self.root)
        # if on FriendGroup level
        if hasattr(pointer, 'users'):
            return len(pointer.users)
        return 0

    def index(self, row, column, parentIndex):
        pointer = parentIndex.internalPointer()
        # if root element, use root list
        if pointer is None:
            return self.createIndex(row, column, self.root[row])
        # if on FriendGroup level
        if hasattr(pointer, 'users'):
            return self.createIndex(row, column, pointer.users[row])
        print 'no'
        return self.createIndex(row, column, None)

    def data(self, index, role):
        if not index.isValid():
            return None
        pointer = index.internalPointer()
        if role == QtCore.Qt.DecorationRole and isinstance(pointer, User) and index.column() == 0:
            if pointer.avatarNotLoaded:
                pointer.loadPixmap()
                if not pointer.avatarNotLoaded:
                    print 'loaded'
                    self.emit(QtCore.SIGNAL('modelChanged'), index, index)
            return pointer.pix

        if role == QtCore.Qt.UserRole:
            if isinstance(pointer, FriendGroup):
                return None
            if index.column() == 0:
                return pointer.username

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.UserRole:
            if isinstance(pointer, FriendGroup):
                if index.column() == 0:
                    return pointer.name
                return None
            else:
                if index.column() == 1:
                    return pointer.country
                if index.column() == 2:
                    return pointer.rating
                if index.column() == 3:
                    return '#'
                return pointer.name

        return None

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        pointer = index.internalPointer()
        if hasattr(pointer, 'users'):
            return QtCore.QModelIndex()
        else:
            row = 0 if pointer.group == 'online' else 1
            return self.createIndex(row, 0, pointer.group)
