from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QNetworkRequest
from chat._avatarWidget import AvatarWidget

import urllib.request, urllib.error, urllib.parse
import chat
from fa.replay import replay
import util
import client
from config import Settings
from client.players import PlayerColors, PlayerAffiliation

"""
A chatter is the representation of a person on IRC, in a channel's nick list.
There are multiple chatters per channel.
There can be multiple chatters for every Player in the Client.
"""


class Chatter(QtWidgets.QTableWidgetItem):
    SORT_COLUMN = 2
    AVATAR_COLUMN = 1
    RANK_COLUMN = 0
    STATUS_COLUMN = 3

    RANK_ELEVATION = 0
    RANK_FRIEND = 1
    RANK_USER = 2
    RANK_NONPLAYER = 3
    RANK_FOE = 4

    def __init__(self, parent, user, lobby, *args, **kwargs):
        QtWidgets.QTableWidgetItem.__init__(self, *args, **kwargs)

        # TODO: for now, userflags and ranks aren't properly interpreted :-/
        # This is impractical if an operator reconnects too late.
        self.parent = parent
        self.lobby = lobby

        self.name, self.id, self.elevation, self.hostname = user

        self.avatar = None
        self.status = None
        self.rating = None
        self.country = None
        self.league = None
        self.clan = ""
        self.avatarTip = ""

        self.setText(self.name)
        self.setFlags(QtCore.Qt.ItemIsEnabled)
        self.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        row = self.parent.rowCount()
        self.parent.insertRow(row)

        self.parent.setItem(row, Chatter.SORT_COLUMN, self)

        self.avatarItem = QtWidgets.QTableWidgetItem()
        self.avatarItem.setFlags(QtCore.Qt.ItemIsEnabled)
        self.avatarItem.setTextAlignment(QtCore.Qt.AlignHCenter)

        self.rankItem = QtWidgets.QTableWidgetItem()
        self.rankItem.setFlags(QtCore.Qt.ItemIsEnabled)
        self.rankItem.setTextAlignment(QtCore.Qt.AlignHCenter)

        self.statusItem = QtWidgets.QTableWidgetItem()
        self.statusItem.setFlags(QtCore.Qt.ItemIsEnabled)
        self.statusItem.setTextAlignment(QtCore.Qt.AlignHCenter)

        self.parent.setItem(self.row(), Chatter.RANK_COLUMN, self.rankItem)
        self.parent.setItem(self.row(), Chatter.AVATAR_COLUMN, self.avatarItem)
        self.parent.setItem(self.row(), Chatter.STATUS_COLUMN, self.statusItem)

        self.update()

    def isFiltered(self, filter):
        if filter in (self.clan or "").lower() or filter in self.name.lower():
            return True
        return False

    def setVisible(self, visible):
        if visible:
            self.tableWidget().showRow(self.row())
        else:
            self.tableWidget().hideRow(self.row())

    def __ge__(self, other):
        """ Comparison operator used for item list sorting """
        return not self.__lt__(other)

    def __lt__(self, other):
        """ Comparison operator used for item list sorting """
        firstStatus = self.getUserRank(self)
        secondStatus = self.getUserRank(other)

        if self.name == self.lobby.client.login: return True
        if other.name == self.lobby.client.login: return False

        # if not same rank sort
        if firstStatus != secondStatus:
            return firstStatus < secondStatus

        # Default: Alphabetical
        return self.name.lower() < other.name.lower()

    def getUserRank(self, other):
        # TODO: Add subdivision for admin?
        me = self.lobby.client.me

        if other.elevation:
            return self.RANK_ELEVATION
        if me.isFriend(other.id, other.name):
            return self.RANK_FRIEND - (2 if self.lobby.client.friendsontop else 0)
        if me.isFoe(other.id, other.name):
            return self.RANK_FOE
        if self.lobby.client.players.is_player(other.id):
            return self.RANK_USER

        return self.RANK_NONPLAYER

    def isMod(self):
        return self.elevation not in [None, ''] and self.elevation in "~&@%+"

    def updateAvatar(self):
        if self.avatar:

            self.avatarTip = self.avatar["tooltip"]
            self.avatar["url"] = urllib.parse.unquote(self.avatar["url"])
            url = self.avatar["url"]

            avatarPix = util.respix(url)

            if avatarPix:
                self.avatarItem.setIcon(QtGui.QIcon(avatarPix))
                self.avatarItem.setToolTip(self.avatarTip)
            else:
                if util.addcurDownloadAvatar(url, self.name):
                    self.lobby.nam.get(QNetworkRequest(QtCore.QUrl(url)))
        else:
            # No avatar set.
            self.avatarItem.setIcon(QtGui.QIcon())
            self.avatarItem.setToolTip(None)

    def update(self):
        """
        Updates the appearance of this chatter in the nicklist
         according to its lobby and irc states
        """
        self.setText(self.name)
        # First make sure we've got the correct id for ourselves
        if self.id == -1 and self.lobby.client.players.is_player(self.name):
            self.id = self.lobby.client.players.get_id(self.name)

        # Color handling
        self.set_color()

        player = self.lobby.client.players[self.id]
        if not player and not self.id == -1:  # We should have a player object for this
            player = self.lobby.client.players[self.name]

        # Weed out IRC users and those we don't know about early.
        if self.id == -1 or player is None:
            self.rankItem.setIcon(util.THEME.icon("chat/rank/civilian.png"))
            self.rankItem.setToolTip("IRC User")
            return

        country = player.country
        if country is not None:
            self.setIcon(util.THEME.icon("chat/countries/%s.png" % country.lower()))
            self.setToolTip(country)

        if player.avatar != self.avatar:
            self.avatar = player.avatar
            self.updateAvatar()

        self.rating = player.rating_estimate()

        self.clan = player.clan
        if self.clan is not None:
            self.setText("[%s]%s" % (self.clan,self.name))

        rating = self.rating
        ladder_rating = player.ladder_estimate()

        # Status icon handling
        url = client.instance.urls.get(player.login)
        if url:
            if url.scheme() == "fafgame":
                self.statusItem.setIcon(util.THEME.icon("chat/status/lobby.png"))
                self.statusItem.setToolTip("In Game Lobby<br/>"+url.toString())
            elif url.scheme() == "faflive":
                self.statusItem.setIcon(util.THEME.icon("chat/status/playing.png"))
                self.statusItem.setToolTip("Playing Game<br/>"+url.toString())
        else:
            self.statusItem.setIcon(QtGui.QIcon())
            self.statusItem.setToolTip("Idle")

        # Rating icon choice  (chr(0xB1) = +-)
        self.rankItem.setToolTip("Global Rating: " + str(int(rating)) + " (" + str(player.number_of_games) + " Games) ["
                                 + str(int(player.rating_mean)) + chr(0xB1) + str(int(player.rating_deviation)) +
                                 "]\nLadder Rating: " + str(int(ladder_rating)) + " [" +
                                 str(int(player.ladder_rating_mean)) + chr(0xB1) + str(int(player.ladder_rating_deviation)) + "]")

        league = player.league
        if league is not None:
            self.rankItem.setToolTip("Division : " + league["division"] + "\nGlobal Rating: " + str(int(rating)))
            self.rankItem.setIcon(util.THEME.icon("chat/rank/%s.png" % league["league"]))
        else:
            self.rankItem.setIcon(util.THEME.icon("chat/rank/newplayer.png"))

    def set_color(self):
        # FIXME - we should really get players and me in the constructor
        affiliation = self.lobby.client.me.getAffiliation(self.id, self.name)
        if self.isMod():
            if affiliation == PlayerAffiliation.SELF:
                self.setForeground(QtGui.QColor(chat.get_color("self_mod")))
            elif affiliation in [PlayerAffiliation.FRIEND, PlayerAffiliation.CLANNIE]:
                self.setForeground(QtGui.QColor(chat.get_color("friend_mod")))
            else:
                self.setForeground(QtGui.QColor(chat.colors.OPERATOR_COLORS[self.elevation]))
            return

        if self.id != -1:
            seed = self.name
        else:
            seed = self.id

        self.setForeground(QtGui.QColor(PlayerColors.get_user_color(
            affiliation, irc=self.id == -1,
            random_color=self.lobby.client.players.coloredNicknames, seed=self.name
        )))

    def viewAliases(self):
        QtGui.QDesktopServices.openUrl(QUrl("{}?name={}".format(Settings.get("USER_ALIASES_URL"), self.name)))

    def selectAvatar(self):
        avatarSelection = AvatarWidget(self.lobby.client, self.name, personal=True)
        avatarSelection.exec_()

    def addAvatar(self):
        avatarSelection = AvatarWidget(self.lobby.client, self.name)
        avatarSelection.exec_()

    def kick(self):
        pass

    def doubleClicked(self, item):
        # filter yourself
        if self.lobby.client.login == self.name:
            return
        # Chatter name clicked
        if item == self:
            self.lobby.openQuery(self.name, self.id, activate=True)  # open and activate query window

        elif item == self.statusItem:
            if self.name in client.instance.urls:
                url = client.instance.urls[self.name]
                if url.scheme() == "fafgame":
                    self.joinInGame()
                elif url.scheme() == "faflive":
                    self.viewReplay()

    def pressed(self, item):
        menu = QtWidgets.QMenu(self.parent)

        # Actions for stats
        actionSelectAvatar = QtWidgets.QAction("Select Avatar", menu)

        # Action for aliases link
        actionViewAliases = QtWidgets.QAction("View Aliases", menu)

        # Actions for Games and Replays
        actionReplay = QtWidgets.QAction("View Live Replay", menu)
        actionVaultReplay = QtWidgets.QAction("View Replays in Vault", menu)
        actionJoin = QtWidgets.QAction("Join in Game", menu)

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
        actionViewAliases.triggered.connect(self.viewAliases)
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
            actionAddAvatar = QtWidgets.QAction("Assign avatar", menu)
            menu.addAction(actionAddAvatar)
            actionAddAvatar.triggered.connect(self.addAvatar)

            if self.lobby.client.power == 2:
                action_inspect_in_mordor = QtWidgets.QAction("Send the Orcs", menu)
                menu.addAction(action_inspect_in_mordor)

                def send_the_orcs():
                    route = Settings.get('mordor/host')

                    if self.id != -1:
                        QtGui.QDesktopServices.openUrl(QUrl("{}/users/{}".format(route, self.id)))
                    else:
                        QtGui.QDesktopServices.openUrl(QUrl("{}/users/{}".format(route, self.name)))

                action_inspect_in_mordor.triggered.connect(send_the_orcs)

                actionCloseFA = QtWidgets.QAction("Close Game", menu)
                menu.addAction(actionCloseFA)
                actionCloseFA.triggered.connect(lambda: self.lobby.client.closeFA(self.name))

                actionCloseLobby = QtWidgets.QAction("Close FAF Client", menu)
                menu.addAction(actionCloseLobby)
                actionCloseLobby.triggered.connect(lambda: self.lobby.client.closeLobby(self.name))

            menu.addSeparator()

        # Adding to menu
        menu.addSeparator
        menu.addAction(actionViewAliases)
        menu.addSeparator()
        menu.addAction(actionReplay)
        menu.addAction(actionVaultReplay)
        menu.addSeparator()
        menu.addAction(actionJoin)

        # Actions for the Friends List
        actionAddFriend = QtWidgets.QAction("Add friend", menu)
        actionRemFriend = QtWidgets.QAction("Remove friend", menu)

        # Actions for the Foes List
        actionAddFoe = QtWidgets.QAction("Add foe", menu)
        actionRemFoe = QtWidgets.QAction("Remove foe", menu)

        # Triggers
        if self.id != -1:
            actionAddFriend.triggered.connect(lambda: self.lobby.client.addFriend(self.id))
            actionRemFriend.triggered.connect(lambda: self.lobby.client.remFriend(self.id))
            actionAddFoe.triggered.connect(lambda: self.lobby.client.addFoe(self.id))
            actionRemFoe.triggered.connect(lambda: self.lobby.client.remFoe(self.id))
        else:
            # We're an IRC chatter
            actionAddFriend.triggered.connect(lambda: self.lobby.client.me.addIrcFriend(self.name))
            actionRemFriend.triggered.connect(lambda: self.lobby.client.me.remIrcFriend(self.name))
            actionAddFoe.triggered.connect(lambda: self.lobby.client.me.addIrcFoe(self.name))
            actionRemFoe.triggered.connect(lambda: self.lobby.client.me.remIrcFoe(self.name))

        # Add actions according to friend status
        actionAddFriend.setDisabled(True)
        actionRemFriend.setDisabled(True)
        actionAddFoe.setDisabled(True)
        actionRemFoe.setDisabled(True)

        me = self.lobby.client.me
        if me.player.id == self.id:
            pass    # We're ourselves
        elif me.isFriend(self.id, self.name):
            actionRemFriend.setDisabled(False)# We're a friend
            menu.addAction(actionRemFriend)
        elif me.isFoe(self.id, self.name):
            actionRemFoe.setDisabled(False) # We're a foe
            menu.addAction(actionRemFoe)
        else:
            actionAddFriend.setDisabled(False) # We're neither
            actionAddFoe.setDisabled(False)
            menu.addAction(actionAddFriend)
            # FIXME - chatwidget sets mod status very inconsistently
            # so disable foeing mods for now
            if not self.isMod():
                menu.addSeparator()
                menu.addAction(actionAddFoe)

        # Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())

    def viewReplay(self):
        if self.name in client.instance.urls:
            replay(client.instance.urls[self.name])

    def viewVaultReplay(self):
        """ see the player replays in the vault """
        self.lobby.client.replays.setCurrentIndex(2)  # focus on Online Fault
        replayHandler = self.lobby.client.replays.vaultManager
        replayHandler.searchVault(0, "", self.name, 0)
        self.lobby.client.mainTabs.setCurrentIndex(self.lobby.client.mainTabs.indexOf(self.lobby.client.replaysTab))

    def joinInGame(self):
        if self.name in client.instance.urls:
            client.instance.joinGameFromURL(client.instance.urls[self.name])
