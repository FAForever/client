from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QNetworkRequest
from chat._avatarWidget import avatarWidget

import urllib.request, urllib.error, urllib.parse
import chat
from fa.replay import replay
import util
import client
from config import Settings
from model.playerset import PlayerColors
from client.user import PlayerAffiliation

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
        if self.lobby.client.players.isPlayer(other.id):
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
        if self.id == -1 and self.lobby.client.players.isPlayer(self.name):
            self.id = self.lobby.client.players.getID(self.name)

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

        self.setForeground(QtGui.QColor(PlayerColors.getUserColor(
            affiliation, irc=self.id == -1,
            random=self.lobby.client.players.coloredNicknames, seed=self.name
        )))

    def viewAliases(self):
        QtGui.QDesktopServices.openUrl(QUrl("{}?name={}".format(Settings.get("USER_ALIASES_URL"), self.name)))

    def selectAvatar(self):
        avatarSelection = avatarWidget(self.lobby.client, self.name, personal=True)
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

        def menu_add(action_str, action_connect, separator=False):
            if separator:
                menu.addSeparator()
            action = QtWidgets.QAction(action_str, menu)
            action.triggered.connect(action_connect)  # Triggers
            menu.addAction(action)

        # only for us. Either way, it will display our avatar, not anyone avatar.
        if self.lobby.client.login == self.name:
            menu_add("Select Avatar", self.selectAvatar)

        # power menu
        if self.lobby.client.power > 1:
            # admin and mod menus
            menu_add("Assign avatar", self.addAvatar, True)

            if self.lobby.client.power == 2:

                def send_the_orcs():
                    route = Settings.get('mordor/host')
                    if self.id != -1:
                        QtGui.QDesktopServices.openUrl(QUrl("{}/users/{}".format(route, self.id)))
                    else:
                        QtGui.QDesktopServices.openUrl(QUrl("{}/users/{}".format(route, self.name)))

                menu_add("Send the Orcs", send_the_orcs, True)
                menu_add("Close Game", lambda: self.lobby.client.closeFA(self.name))
                menu_add("Close FAF Client", lambda: self.lobby.client.closeLobby(self.name))

        # Aliases link
        menu_add("View Aliases", self.viewAliases, True)

        # Joining hosted or live Game
        if self.lobby.client.login != self.name:  # Don't allow self to be invited to a game, or join one
            if self.name in client.instance.urls:

                url = client.instance.urls[self.name]
                if url.scheme() == "fafgame":
                    menu_add("Join hosted Game", self.joinInGame, True)
                elif url.scheme() == "faflive":
                    menu_add("View live Replay", self.viewReplay, True)

        # Replays in vault
        if self.id != -1:  # not for irc user
            menu_add("View Replays in Vault", self.viewVaultReplay, True)

        # Friends and Foes Lists
        def player_or_irc_action_connect(f, irc_f):  # Irc or not Irc, that's the Question
            if self.id != -1:
                return lambda: f(self.id)
            else:
                return lambda: irc_f(self.name)

        cl = self.lobby.client
        me = self.lobby.client.me
        if me.player.id == self.id:  # We're ourselves
            pass

        elif me.isFriend(self.id, self.name):  # We're a friend

            menu_add("Remove friend", player_or_irc_action_connect(cl.remFriend, me.remIrcFriend), True)

        elif me.isFoe(self.id, self.name):  # We're a foe

            menu_add("Remove foe", player_or_irc_action_connect(cl.remFoe, me.remIrcFoe), True)

        else:  # We're neither

            menu_add("Add friend", player_or_irc_action_connect(cl.addFriend, me.addIrcFriend), True)

            # FIXME - chatwidget sets mod status very inconsistently
            if not self.isMod():  # so disable foeing mods for now
                menu_add("Add foe", player_or_irc_action_connect(cl.addFoe, me.addIrcFoe))

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
