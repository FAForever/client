from PyQt4 import QtCore, QtGui
import util, client, friendlist

FormClass, BaseClass = util.loadUiType("friendlist/friendlist.ui")
class FriendListDialog(FormClass, BaseClass):
    def __init__(self, friendListModel, client):
        BaseClass.__init__(self, client)
        self.client = client
        self.client.sidebar.hide()

        self.setupUi(self)

        self.friendListModel = friendListModel
        self.friendListModel.remove_user.connect(self.removeFriend)
        self.friendListModel.add_user.connect(self.addFriend)
        self.friendListModel.update_user.connect(self.updateGameStatus)
        self.model = FriendListModel(friendListModel.groups, client)

        # proxy model for sorting
        self.proxy = QtGui.QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(QtCore.Qt.UserRole)
        self.friendlist.setModel(self.proxy)

        # modify he width of columns
        self.friendlist.header().setStretchLastSection(False);
        self.friendlist.header().resizeSection (FriendListModel.COL_INGAME, 18)
        self.friendlist.header().resizeSection (FriendListModel.COL_RATING, 42)

        # stretch first column
        self.friendlist.header().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.friendlist.expandAll()

        # place on the the lobby
        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self)
        self.client.friendlistWidget.setLayout(layout)

    def addFriend(self, groupIndex, username):
        '''
        groupIndex: 0 = online, 1 = offline
        '''
        n = len(self.model.root[groupIndex].users)
        self.model.beginInsertRows(self.model.index(groupIndex, 0, QtCore.QModelIndex()), n, n)
        self.model.root[groupIndex].addUser(username)
        self.model.endInsertRows()

    def removeFriend(self, groupIndex, username):
        row = self.model.root[groupIndex].getRowOfUser(username)
        self.model.beginRemoveRows(self.model.index(groupIndex, 0, QtCore.QModelIndex()), row, row)
        self.model.root[groupIndex].removeUser(username)
        self.model.endRemoveRows()

    def updateGameStatus(self, username):
        row = self.model.root[self.friendListModel.ONLINE].getRowOfUser(username)
        user = self.model.root[self.friendListModel.ONLINE].getUser(username)
        modelIndex = self.model.createIndex(row, FriendListModel.COL_INGAME, user)
        self.model.dataChanged.emit(modelIndex, modelIndex)

    def getUserNameFromModel(self, modelIndex):
        if modelIndex == None or not modelIndex.isValid():
            return False
        pointer = self.proxy.mapToSource(modelIndex).internalPointer()
        if pointer == None:
            return False
        # if a group and not a user
        if not hasattr(pointer, 'username'):
            return False
        return pointer.username

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def on_friendlist_doubleClicked(self, modelIndex):
        playername = self.getUserNameFromModel(modelIndex)
        if not playername:
            return
        self.client.api.openPrivateChat(playername)

    @QtCore.pyqtSlot(QtCore.QPoint)
    def on_friendlist_customContextMenuRequested(self, pos):
        modelIndex = self.friendlist.indexAt(pos)
        playername = self.getUserNameFromModel(modelIndex)
        if not playername:
            return

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
        if not (self.api.isMe(playername)):
            playerStatus = self.api.getPlayerStatus(playername)
            if playerStatus == self.api.STATUS_INGAME_LOBBY:
                actionJoin.setEnabled(True)
            elif playerStatus == self.api.STATUS_PLAYING:
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
    COL_RATING = 2

    def __init__(self, groups, client):
        QtCore.QAbstractItemModel.__init__(self)
        self.root = groups
        self.client = client
        self.api = client.api

        self.header = ['Player', ' ', 'Rating']

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
        if role == QtCore.Qt.DecorationRole and isinstance(pointer, friendlist.User):
            if index.column() == self.COL_PLAYER:
                if pointer.avatarNotLoaded:
                    pointer.loadPixmap()
                    if not pointer.avatarNotLoaded:
                        self.emit(QtCore.SIGNAL('modelChanged'), index, index)
                return pointer.pix
            if  index.column() == self.COL_INGAME:
                playerStatus = self.api.getPlayerStatus(pointer.username)
                if playerStatus == self.api.STATUS_INGAME_LOBBY:
                    return util.icon("chat/status/lobby.png")
                elif playerStatus == self.api.STATUS_PLAYING:
                    return util.icon("chat/status/playing.png")
                return None

        # for sorting
        if role == QtCore.Qt.UserRole:
            if isinstance(pointer, friendlist.FriendGroup):
                return None
            if index.column() == self.COL_PLAYER:
                return pointer.username.lower()
            if index.column() == self.COL_INGAME:
                playerStatus = self.api.getPlayerStatus(pointer.username)
                if playerStatus == self.api.STATUS_INGAME_LOBBY:
                    return 1
                elif playerStatus == self.api.STATUS_PLAYING:
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
                if index.column() == self.COL_RATING:
                    return pointer.rating
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
