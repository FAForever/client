from PyQt4 import QtGui, QtCore
from PyQt4.QtNetwork import QNetworkRequest
from chat._avatarWidget import avatarWidget


from chat import user2name
from fa.replay import replay
import util

import client


class Chatter(QtGui.QTableWidgetItem):
    SORT_COLUMN = 2
    AVATAR_COLUMN = 1
    RANK_COLUMN = 0
    STATUS_COLUMN = 3

    RANK_ELEVATION = 0
    RANK_FRIEND = 1
    RANK_USER = 2
    RANK_FOE = 3
    RANK_NONPLAYER = 4

    '''
    A chatter is the representation of a person on IRC, in a channel's nick list. There are multiple chatters per channel.
    There can be multiple chatters for every Player in the Client.
    '''
    def __init__(self, parent, user, lobby, *args, **kwargs):
        QtGui.QTableWidgetItem.__init__(self, *args, **kwargs)
                
        #TODO: for now, userflags and ranks aren't properly interpreted :-/ This is impractical if an operator reconnects too late.
        self.parent = parent
        self.lobby = lobby

        if user[0] in self.lobby.OPERATOR_COLORS:
            self.elevation = user[0]
        else:
            self.elevation = None

        self.name = user2name(user)
        
        self.avatar = None
        self.status = None
        self.rating = None
        self.country = None
        self.league = None
        self.clan = ""
        self.avatarTip = ""
        
        self.setup()
    
    def setup(self):
        self.setText(self.name)
        self.setFlags(QtCore.Qt.ItemIsEnabled)        
        self.setTextAlignment(QtCore.Qt.AlignLeft)

        row = self.parent.rowCount()
        self.parent.insertRow(row)
        
        self.parent.setItem(row, Chatter.SORT_COLUMN, self)
        
        self.avatarItem = QtGui.QTableWidgetItem()
        self.avatarItem.setFlags(QtCore.Qt.ItemIsEnabled)
        self.avatarItem.setTextAlignment(QtCore.Qt.AlignHCenter)
        
        self.rankItem = QtGui.QTableWidgetItem()
        self.rankItem.setFlags(QtCore.Qt.ItemIsEnabled)
        self.rankItem.setTextAlignment(QtCore.Qt.AlignHCenter)

        self.statusItem = QtGui.QTableWidgetItem()
        self.statusItem.setFlags(QtCore.Qt.ItemIsEnabled)
        self.statusItem.setTextAlignment(QtCore.Qt.AlignHCenter)

        self.parent.setItem(self.row(), Chatter.RANK_COLUMN, self.rankItem)
        self.parent.setItem(self.row(), Chatter.AVATAR_COLUMN, self.avatarItem)
        self.parent.setItem(self.row(), Chatter.STATUS_COLUMN, self.statusItem)

        self.update()        


    def isFiltered(self, filter):
        if filter in self.clan.lower() or filter in self.name.lower():
            return True
        return False

    def setVisible(self, visible):        
        if visible:
            self.tableWidget().showRow(self.row())
        else:
            self.tableWidget().hideRow(self.row())
              
    def __ge__(self, other):
        ''' Comparison operator used for item list sorting '''        
        return not self.__lt__(other)

    def __lt__(self, other):
        ''' Comparison operator used for item list sorting '''
        firstStatus = self.getUserRank(self)
        secondStatus = self.getUserRank(other)
        # if not same rank sort
        if firstStatus != secondStatus:
            return firstStatus < secondStatus

        # List self below all friends and above every other player
        if self.name == self.lobby.client.login: return True
        if other.name == self.lobby.client.login: return False
        
        # Default: Alphabetical
        return self.name.lower() < other.name.lower()

    def getUserRank(self, user):
        # TODO: Add subdivision for admin?
        if user.elevation:
            return self.RANK_ELEVATION
        if self.lobby.client.isFriend(user.name):
            return self.RANK_FRIEND
        if self.lobby.client.isFoe(user.name):
            return self.RANK_FOE
        if self.lobby.client.isPlayer(user.name):
            return self.RANK_USER
        return self.RANK_NONPLAYER


    def updateAvatar(self):
        if self.avatar:        
            
            self.avatarTip = self.avatar["tooltip"]           
            url = self.avatar["url"]

            avatarPix = util.respix(url) 

            if avatarPix :
                self.avatarItem.setIcon(QtGui.QIcon(avatarPix))            
                self.avatarItem.setToolTip(self.avatarTip)
            else:                           
                if util.addcurDownloadAvatar(url, self.name) :                
                    self.lobby.nam.get(QNetworkRequest(QtCore.QUrl(url)))            
        else:
            # No avatar set.
            self.avatarItem.setIcon(QtGui.QIcon()) 
            self.avatarItem.setToolTip(None)

    def update(self):
        '''
        updates the appearance of this chatter in the nicklist according to its lobby and irc states 
        '''        

        # Weed out IRC users early.
        if self.name not in self.lobby.client.players:
            self.rankItem.setIcon(util.icon("chat/rank/civilian.png"))
            self.rankItem.setToolTip("IRC User")
            return

        player = self.lobby.client.players[self.name]

        country = player.country
        if country is not None :
            self.setIcon(util.icon("chat/countries/%s.png" % country.lower()))
            self.setToolTip(country)

        if player.avatar != self.avatar:
            self.avatar = player.avatar
            self.updateAvatar()

        self.rating = player.get_ranking()

        self.clan = player.clan
        if self.clan is not None:
            self.setText("[%s]%s" % (self.clan,self.name))

        # Color handling
        self.setChatUserColor(self.name)

        rating = self.rating

        # Status icon handling
        if self.name in client.instance.urls:
            url = client.instance.urls[self.name]
            if url:
                if url.scheme() == "fafgame":
                    self.statusItem.setIcon(util.icon("chat/status/lobby.png"))
                    self.statusItem.setToolTip("In Game Lobby<br/>"+url.toString())
                elif url.scheme() == "faflive":
                    self.statusItem.setIcon(util.icon("chat/status/playing.png"))
                    self.statusItem.setToolTip("Playing Game<br/>"+url.toString())
        else:
            self.statusItem.setIcon(QtGui.QIcon())
            self.statusItem.setToolTip("Idle")

        #Rating icon choice
        #TODO: These are very basic and primitive
        self.rankItem.setToolTip("Global Rating: " + str(int(rating)))

        league = player.league
        if league is not None:
            self.rankItem.setToolTip("Division : " + league["division"]+ "\nGlobal Rating: " + str(int(rating)))
            self.rankItem.setIcon(util.icon("chat/rank/%s.png" % league["league"]))
        else:
            self.rankItem.setIcon(util.icon("chat/rank/newplayer.png"))

    def setChatUserColor(self, username):
        if self.lobby.client.isFriend(username):
            if self.elevation in self.lobby.OPERATOR_COLORS:
                self.setTextColor(QtGui.QColor(self.lobby.client.getColor("friend_mod")))
                return
            self.setTextColor(QtGui.QColor(self.lobby.client.getColor("friend")))
            return
        if self.elevation in self.lobby.OPERATOR_COLORS:
            self.setTextColor(QtGui.QColor(self.lobby.OPERATOR_COLORS[self.elevation]))
            return
        if self.name in self.lobby.client.colors :
            self.setTextColor(QtGui.QColor(self.lobby.client.getColor(self.name)))
            return
        self.setTextColor(QtGui.QColor(self.lobby.client.getUserColor(self.name)))

    def selectAvatar(self):
        avatarSelection = avatarWidget(self.lobby.client, self.name, personal = True)
        avatarSelection.exec_()

    def addAvatar(self):
        avatarSelection = avatarWidget(self.lobby.client, self.name)
        avatarSelection.exec_()

    def kick(self):
        pass

    def doubleClicked(self, item):
        # filter yourself
        if self.lobby.client.login == self.name:
            return
        # Chatter name clicked
        if item == self:
            self.lobby.openQuery(self.name, True)  # open and activate query window

        elif item == self.statusItem:
            if self.name in client.instance.urls:
                url = client.instance.urls[self.name]
                if url.scheme() == "fafgame":
                    self.lobby.client.api.joinInGame(self.name)
                elif url.scheme() == "faflive":
                    self.lobby.client.api.viewLiveReplay(self.name)

    def pressed(self, item):        
        menu = QtGui.QMenu(self.parent)

        # Actions for stats
        actionSelectAvatar  = QtGui.QAction("Select Avatar", menu)
        
        # Actions for Games and Replays
        actionReplay = QtGui.QAction("View Live Replay", menu)
        actionVaultReplay = QtGui.QAction("View Replays in Vault", menu)
        actionJoin = QtGui.QAction("Join in Game", menu)

        # Default is all disabled, we figure out what we can do after this
        actionReplay.setDisabled(True)
        actionJoin.setDisabled(True)

        # Don't allow self to be invited to a game, or join one
        if self.lobby.client.login != self.name:
            if self.name in client.instance.urls:
                url = client.instance.urls[self.name]
                if url.scheme() == "fafgame":
                    actionJoin.setEnabled(True)
                elif url.scheme() == "faflive":
                    actionReplay.setEnabled(True)

        # Triggers
        actionSelectAvatar.triggered.connect(self.selectAvatar)
        actionReplay.triggered.connect(self.viewReplay)
        actionVaultReplay.triggered.connect(self.viewVaultReplay)
        actionJoin.triggered.connect(self.joinInGame)
        
        # only for us. Either way, it will display our avatar, not anyone avatar.
        if self.lobby.client.login == self.name :
            menu.addAction(actionSelectAvatar)
            menu.addSeparator()
      
        # power menu
        if self.lobby.client.power > 1:
            # admin and mod menus
            actionAddAvatar = QtGui.QAction("Assign avatar", menu)
            menu.addAction(actionAddAvatar)
            actionAddAvatar.triggered.connect(self.addAvatar)
            
            if self.lobby.client.power == 2:
                actionCloseFA = QtGui.QAction("Close FA", menu)
                menu.addAction(actionCloseFA)
                actionCloseFA.triggered.connect(lambda: self.lobby.client.closeFA(self.name))

                actionCloseLobby = QtGui.QAction("Kick from Lobby", menu)
                menu.addAction(actionCloseLobby)
                actionCloseLobby.triggered.connect(lambda: self.lobby.client.closeLobby(self.name))
      
            menu.addSeparator()

        # Adding to menu
        menu.addSeparator()
        menu.addAction(actionReplay)
        menu.addAction(actionVaultReplay)
        menu.addSeparator()
        menu.addAction(actionJoin)

        # Actions for the Friends List
        actionAddFriend = QtGui.QAction("Add friend", menu)
        actionRemFriend = QtGui.QAction("Remove friend", menu)

        # Actions for the Foes List
        actionAddFoe = QtGui.QAction("Add foe", menu)
        actionRemFoe = QtGui.QAction("Remove foe", menu)
        
        # Don't allow self to be added or removed from friends or foes
        if self.lobby.client.login == self.name:
            actionAddFriend.setDisabled(1)
            actionRemFriend.setDisabled(1)
            actionAddFoe.setDisabled(1)
            actionRemFoe.setDisabled(1)
              
        # Enable / Disable actions according to friend status  
        if self.lobby.client.isFriend(self.name):
            actionAddFriend.setDisabled(1)
            actionRemFoe.setDisabled(1)
            actionAddFoe.setDisabled(1)
        else:
            actionRemFriend.setDisabled(1)

        if self.lobby.client.isFoe(self.name):
            actionAddFoe.setDisabled(1)
            actionAddFriend.setDisabled(1)
            actionRemFriend.setDisabled(1)
        else:
            actionRemFoe.setDisabled(1)
                                      
        # Triggers
        actionAddFriend.triggered.connect(lambda: self.lobby.client.addFriend(self.name))
        actionRemFriend.triggered.connect(lambda: self.lobby.client.remFriend(self.name))
        actionAddFoe.triggered.connect(lambda: self.lobby.client.addFoe(self.name))
        actionRemFoe.triggered.connect(lambda: self.lobby.client.remFoe(self.name))
      
        # Adding to menu
        menu.addAction(actionAddFriend)
        menu.addAction(actionRemFriend)
        menu.addSeparator()
        menu.addAction(actionAddFoe)
        menu.addAction(actionRemFoe)

        #Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())
            
    @QtCore.pyqtSlot()
    def viewReplay(self):
        if self.name in client.instance.urls:
            replay(client.instance.urls[self.name])

    @QtCore.pyqtSlot()
    def viewVaultReplay(self):
        ''' see the player replays in the vault '''
        self.lobby.client.replays.mapName.setText("")
        self.lobby.client.replays.playerName.setText(self.name)
        self.lobby.client.replays.minRating.setValue(0)
        self.lobby.client.replays.searchVault()
        self.lobby.client.mainTabs.setCurrentIndex(self.lobby.client.mainTabs.indexOf(self.lobby.client.replaysTab))
    

    @QtCore.pyqtSlot()
    def joinInGame(self):
        if self.name in client.instance.urls:
            client.instance.joinGameFromURL(client.instance.urls[self.name])
