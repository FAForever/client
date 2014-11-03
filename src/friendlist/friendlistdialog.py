from PyQt4 import QtCore, QtGui
import util, client, friendlist

FormClass, BaseClass = util.loadUiType("friendlist/friendlist.ui")
class FriendListDialog(FormClass, BaseClass):
    def __init__(self, friendListModel, client):
        BaseClass.__init__(self, client)
        self.client = client

        self.setupUi(self)

        self.updateTopLabel()

        self.friendListModel = friendListModel
        self.model = FriendListModel(friendListModel.groups, client)

        self.proxy = QtGui.QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(QtCore.Qt.UserRole)
        self.friendlist.setModel(self.proxy)

        self.friendlist.header().setStretchLastSection(False);
        self.friendlist.header().resizeSection (FriendListModel.COL_INGAME, 18)
        self.friendlist.header().resizeSection (FriendListModel.COL_LAND, 48)
        self.friendlist.header().resizeSection (FriendListModel.COL_RATING, 64)
        self.friendlist.header().resizeSection (FriendListModel.COL_SORT, 18)

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

    def updateGameStatus(self, username):
        row = self.model.root[self.friendListModel.ONLINE].getRowOfUser(username)
        user = self.model.root[self.friendListModel.ONLINE].getUser(username)
        modelIndex = self.model.createIndex(row, FriendListModel.COL_INGAME, user)
        self.model.dataChanged.emit(modelIndex, modelIndex)

    @QtCore.pyqtSlot(QtCore.QPoint)
    def on_friendlist_customContextMenuRequested(self, pos):

        modelIndex = self.friendlist.indexAt(pos)
        if modelIndex == None or not modelIndex.isValid():
            return
        pointer = self.proxy.mapToSource(modelIndex).internalPointer()
        if pointer == None:
            return
        # if a group and not a user
        if not hasattr(pointer, 'username'):
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

        # Don't allow self to be invited to a game, or join one
        if self.client.login != playername:
            if playername in client.instance.urls:
                url = client.instance.urls[playername]
                if url.scheme() == "fafgame":
                    actionJoin.setEnabled(True)
                elif url.scheme() == "faflive":
                    actionReplay.setEnabled(True)

        # Triggers
        actionStats.triggered.connect(lambda : self.client.api.viewPlayerStats(playername))
        actionReplay.triggered.connect(lambda : self.client.api.viewLiveReplay(playername))
        actionVaultReplay.triggered.connect(lambda : self.client.api.viewVaultReplay(playername))
        actionJoin.triggered.connect(lambda : self.client.api.joinInGame(playername))

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


class FriendListModel(QtCore.QAbstractItemModel):
    COL_PLAYER = 0
    COL_INGAME = 1
    COL_LAND = 2
    COL_RATING = 3
    COL_SORT = 4

    def __init__(self, groups, client):
        QtCore.QAbstractItemModel.__init__(self)
        self.root = groups
        self.client = client

        self.header = ['Player', ' ', 'Land', 'Rating', '#']

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
            user = pointer.users[row]
            return self.createIndex(row, column, user)
        return self.createIndex(row, column, None)

    def data(self, index, role):
        if not index.isValid():
            return None
        pointer = index.internalPointer()
        if role == QtCore.Qt.DecorationRole and isinstance(pointer, friendlist.User) \
        and index.column() == self.COL_PLAYER:
            if pointer.avatarNotLoaded:
                pointer.loadPixmap()
                if not pointer.avatarNotLoaded:
                    self.emit(QtCore.SIGNAL('modelChanged'), index, index)
            return pointer.pix
        if role == QtCore.Qt.DecorationRole and index.column() == self.COL_INGAME:
            # TODO: extract/refactor
            playername = pointer.name
            if playername in client.instance.urls:
                url = client.instance.urls[playername]
                if url.scheme() == "fafgame":
                    return util.icon("chat/status/lobby.png")
                if url.scheme() == "faflive":
                    return util.icon("chat/status/playing.png")
            return None

        # for sorting
        if role == QtCore.Qt.UserRole:
            if isinstance(pointer, friendlist.FriendGroup):
                return None
            if index.column() == self.COL_PLAYER:
                return pointer.username
            if index.column() == self.COL_INGAME:
                playername = pointer.name
                # TODO: extract/refactor
                if playername in client.instance.urls:
                    url = client.instance.urls[playername]
                    if url.scheme() == "fafgame":
                        return 1
                    if url.scheme() == "faflive":
                        return 3
                return 2

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.UserRole:
            if isinstance(pointer, friendlist.FriendGroup):
                if index.column() == self.COL_PLAYER:
                    return pointer.name
                return None
            else:
                if index.column() == self.COL_PLAYER:
                    return pointer.name
                if index.column() == self.COL_LAND:
                    return pointer.country
                if index.column() == self.COL_RATING:
                    return pointer.rating
                if index.column() == self.COL_SORT:
                    return '#'
                return ''

        return None

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        pointer = index.internalPointer()
        if hasattr(pointer, 'users'):
            return QtCore.QModelIndex()
        if hasattr(pointer, 'group'):
            row = pointer.group.id
            return self.createIndex(row, 0, pointer.group)
