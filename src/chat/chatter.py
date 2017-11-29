from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QNetworkRequest
from chat._avatarWidget import AvatarWidget
import time
import urllib.request, urllib.error, urllib.parse
import json

from fa.replay import replay
from fa import maps

import util
import client
from config import Settings
from model.game import GameState

import logging
logger = logging.getLogger(__name__)

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
    MAP_COLUMN = 4

    RANK_ELEVATION = 0
    RANK_FRIEND = 1
    RANK_USER = 2
    RANK_NONPLAYER = 3
    RANK_FOE = 4

    def __init__(self, parent, user, channel, chat_widget, me):
        QtWidgets.QTableWidgetItem.__init__(self, None)

        # TODO: for now, userflags and ranks aren't properly interpreted :-/
        # This is impractical if an operator reconnects too late.
        self.parent = parent
        self.chat_widget = chat_widget
        self.channel = channel

        self._me = me
        self._me.relationsUpdated.connect(self._checkPlayerRelation)
        self._me.ircRelationsUpdated.connect(self._checkUserRelation)

        self.setFlags(QtCore.Qt.ItemIsEnabled)
        self.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.avatarTip = ""

        self.avatarItem = QtWidgets.QTableWidgetItem()
        self.avatarItem.setFlags(QtCore.Qt.ItemIsEnabled)
        self.avatarItem.setTextAlignment(QtCore.Qt.AlignHCenter)

        self.rankItem = QtWidgets.QTableWidgetItem()
        self.rankItem.setFlags(QtCore.Qt.ItemIsEnabled)
        self.rankItem.setTextAlignment(QtCore.Qt.AlignHCenter)

        self.statusItem = QtWidgets.QTableWidgetItem()
        self.statusItem.setFlags(QtCore.Qt.ItemIsEnabled)
        self.statusItem.setTextAlignment(QtCore.Qt.AlignHCenter)

        self.mapItem = QtWidgets.QTableWidgetItem()
        self.mapItem.setFlags(QtCore.Qt.ItemIsEnabled)
        self.mapItem.setTextAlignment(QtCore.Qt.AlignHCenter)

        self._user = None
        self._user_player = None
        self._user_game = None
        # This updates the above three and the widget
        self.user = user

        row = self.parent.rowCount()
        self.parent.insertRow(row)

        self.parent.setItem(row, Chatter.SORT_COLUMN, self)

        self.parent.setItem(self.row(), Chatter.RANK_COLUMN, self.rankItem)
        self.parent.setItem(self.row(), Chatter.AVATAR_COLUMN, self.avatarItem)
        self.parent.setItem(self.row(), Chatter.STATUS_COLUMN, self.statusItem)
        self.parent.setItem(self.row(), Chatter.MAP_COLUMN, self.mapItem)

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        if self._user is not None:
            self.user_player = None  # Clears game as well
            self._user.updated.disconnect(self.updateUser)
            self._user.newPlayer.disconnect(self._set_user_player)

        self._user = value
        self.updateUser()

        if self._user is not None:
            self._user.updated.connect(self.updateUser)
            self._user.newPlayer.connect(self._set_user_player)
            self.user_player = self._user.player

    def _set_user_player(self, user, player):
        self.user_player = player

    @property
    def user_player(self):
        return self._user_player

    @user_player.setter
    def user_player(self, value):
        if self._user_player is not None:
            self.user_game = None
            self._user_player.updated.disconnect(self.updatePlayer)
            self._user_player.newCurrentGame.disconnect(self._set_user_game)

        self._user_player = value
        self.updatePlayer()

        if self._user_player is not None:
            self._user_player.updated.connect(self.updatePlayer)
            self._user_player.newCurrentGame.connect(self._set_user_game)
            self.user_game = self._user_player.currentGame

    def _set_user_game(self, player, game):
        self.user_game = game

    @property
    def user_game(self):
        return self._user_game

    @user_game.setter
    def user_game(self, value):
        if self._user_game is not None:
            self._user_game.gameUpdated.disconnect(self.updateGame)

        self._user_game = value
        self.updateGame()

        if self._user_game is not None:
            self._user_game.gameUpdated.connect(self.updateGame)

    def _checkPlayerRelation(self, players):
        if self.user_player is None:
            return

        if self.user_player.id in players:
            self.set_color()
            self._verifySortOrder()

    def _checkUserRelation(self, users):
        if self.user.name in users:
            self.set_color()
            self._verifySortOrder()

    def isFiltered(self, _filter):
        clan = None if self.user_player is None else self.user_player.clan
        clan = clan if clan is not None else ""
        name = self.user.name
        if _filter in clan.lower() or _filter in name.lower():
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
        self_rank = self.get_user_rank(self)
        other_rank = self.get_user_rank(other)

        if self._me.player is not None:
            if self.user.name == self._me.player.login:
                return True
            if other.user.name == self._me.player.login:
                return False

        # if not same rank sort
        if self_rank != other_rank:
            return self_rank < other_rank

        # Default: Alphabetical
        return self.user.name.lower() < other.user.name.lower()

    def _verifySortOrder(self):
        if self.row() != -1:
            self.channel.verifySortOrder(self)

    def _getIdName(self):
        _id = -1 if self.user_player is None else self.user_player.id
        name = self.user.name
        return _id, name

    def get_user_rank(self, user):
        # TODO: Add subdivision for admin?
        me = self._me
        _id, name = user._getIdName()
        if user.modElevation():
            return self.RANK_ELEVATION
        if me.isFriend(_id, name):
            return self.RANK_FRIEND - (2 if self.chat_widget.client.friendsontop else 0)
        if me.isFoe(_id, name):
            return self.RANK_FOE
        if user.user_player is not None:
            return self.RANK_USER

        return self.RANK_NONPLAYER

    def modElevation(self):
        if not self.user.is_mod(self.channel.name):
            return None
        return self.user.elevation[self.channel.name]

    def updateAvatar(self):
        try:
            avatar = self.user_player.avatar
        except AttributeError:
            avatar = None

        if avatar is not None:
            self.avatarTip = avatar["tooltip"]
            url = urllib.parse.unquote(avatar["url"])
            avatarPix = util.respix(url)

            if avatarPix:
                self.avatarItem.setIcon(QtGui.QIcon(avatarPix))
                self.avatarItem.setToolTip(self.avatarTip)
            else:
                if util.addcurDownloadAvatar(url, self):
                    self.chat_widget.nam.get(QNetworkRequest(QtCore.QUrl(url)))
        else:
            # No avatar set.
            self.avatarItem.setIcon(QtGui.QIcon())
            self.avatarItem.setToolTip(None)

    def updateUser(self):
        self.setText(self.user.name)
        self.set_color()
        self._verifySortOrder()

    def updatePlayer(self):
        self.set_color()

        player = self.user_player
        # Weed out IRC users and those we don't know about early.
        if player is None:
            self.rankItem.setIcon(util.THEME.icon("chat/rank/civilian.png"))
            self.rankItem.setToolTip("IRC User")
            return

        country = player.country
        if country is not None:
            self.setIcon(util.THEME.icon("chat/countries/%s.png" % country.lower()))
            self.setToolTip(country)

        self.updateAvatar()

        if player.clan is not None:
            self.setText("[%s]%s" % (player.clan, self.user.name))

        rating = player.rating_estimate()
        ladder_rating = player.ladder_estimate()

        # Rating icon choice  (chr(0xB1) = +-)
        formatting = ("Global Rating: {} ({} Games) [{}\xb1{}]\n"
                      "Ladder Rating: {} [{}\xb1{}]")
        self.rankItem.setToolTip(formatting.format(
            str(int(rating)),
            str(player.number_of_games),
            str(int(player.rating_mean)),
            str(int(player.rating_deviation)),
            str(int(ladder_rating)),
            str(int(player.ladder_rating_mean)),
            str(int(player.ladder_rating_deviation))))

        league = player.league
        if league is not None:
            formatting = ("Division : {}\n"
                          "Global Rating: {}")
            self.rankItem.setToolTip(formatting.format(
                league["division"],
                str(int(rating))))
            self.rankItem.setIcon(util.THEME.icon("chat/rank/%s.png" % league["league"]))
        else:
            self.rankItem.setIcon(util.THEME.icon("chat/rank/newplayer.png"))

        self._verifySortOrder()

    def updateGame(self):
        # Status icon handling
        game = self.user_game
        player = self.user_player
        if game is not None and not game.closed():
            url = game.url(player.id)
            if game.state == GameState.OPEN:
                self.statusItem.setIcon(util.THEME.icon("chat/status/lobby.png"))
                self.statusItem.setToolTip("In Game Lobby<br/>"+url.toString())
            elif game.state == GameState.PLAYING:
                self.statusItem.setIcon(util.THEME.icon("chat/status/playing.png"))
                self.statusItem.setToolTip("Playing Game<br/>"+url.toString())
        else:
            self.statusItem.setIcon(QtGui.QIcon())
            self.statusItem.setToolTip("Idle")

        self.updateMap()

    def updateMap(self):
        # Map icon handling - if we're in game, show the map if toggled on
        game = self.user_game
        if game is not None and not game.closed() and util.settings.value("chat/chatmaps", False):
            mapname = game.mapname
            icon = maps.preview(mapname)
            if not icon:
                self.chat_widget.client.downloader.downloadMapPreview(mapname, self.mapItem)  # Calls setIcon
            else:
                self.mapItem.setIcon(icon)

            self.mapItem.setToolTip(game.mapdisplayname)
        else:
            self.mapItem.setIcon(QtGui.QIcon())
            self.mapItem.setToolTip("")

    def update(self):
        self.updateUser()
        self.updatePlayer()
        self.updateGame()

    def set_color(self):
        # FIXME - we should really get colors in the constructor
        pcolors = self.chat_widget.client.player_colors
        elevation = self.modElevation()
        _id, name = self._getIdName()
        if elevation is not None:
            color = pcolors.getModColor(elevation, _id, name)
        else:
            color = pcolors.getUserColor(_id, name)
        self.setForeground(QtGui.QColor(color))

    def returnDecodedJson(self, link, method):
        try:
            with urllib.request.urlopen(link) as response :
                return json.loads(response.read().decode())
        except urllib.error.URLError as e:
            logger.error(method+" method error (link : " + link + " ) : "+str(e.reason))
            QtWidgets.QMessageBox.about(self.parent, "Aliases", "Error getting info, report the issue with logs on the faf forum")
            return 'err'
        except urllib.error.HTTPError as e:
            logger.error(method+" method error (link : " + link + " ) : "+str(e.code+ ':' +e.reason))
            QtWidgets.QMessageBox.about(self.parent, "Aliases", "Error getting info, report the issue with logs on the faf forum")
            return 'err'

    def nickUsedByOther(self, resp):
        result=''
        apiLink='https://api.faforever.com/data/player?include=names&filter=(login=='+self.user.name+',names.name=='+self.user.name+')'
        resp=self.returnDecodedJson(apiLink,'nickUsedByOther')
        if resp =='err':
            return result
        if resp.get('data')!= None and len(resp['data']) >= 1:
            for ply in resp['data']:
                if ply['type']=='player':
                    if ply['attributes']['login'] != self.user.name:
                        result+=(ply['attributes']['login']+'\n')
        if len(result) > 1:
            result = 'It has been previously been used by :\n' + str(result)
        else:
            result='It has never been used by anyone else.'
        return result

    def namesPreviouslyKnown(self):
        nicklists=''
        apiLink='https://api.faforever.com/data/player?include=names&fields[player]=login,names&fields[nameRecord]=name,changeTime&&filter[player]=login=='+self.user.name
        response=self.returnDecodedJson(apiLink,'namesPreviouslyKnown')
        if response == 'err':
            return nicklists
        if response.get('included')!= None and len(response['included']) >= 1:
            nicklists='The player ' + self.user.name + ' has previously been known as :'
            for allnicks in response['included']:
                if allnicks['type']=='nameRecord':
                    nicklists=nicklists+'\n'+allnicks['attributes']['name']
        else:
            nicklists='The name'+ '_Barracuda_' +'is not currently owned by any player.'
        return nicklists

    def viewAliases(self):
        apiLink='https://api.faforever.com/data/nameRecord?include=player&fields[player]=login&fields[nameRecord]=player,changeTime&filter[nameRecord]=name=='+self.user.name
        result=''
        response=self.returnDecodedJson(apiLink,'viewAliases')
        if response=='err':
            return
        result=self.nickUsedByOther(response)
        if len(response['data']) < 1:
            result='The name ' + self.user.name + ' has never been used or the user has never changed its name'+'\n\n'+result
        else:
            result=self.namesPreviouslyKnown()+'\n\n'+result
        QtWidgets.QMessageBox.about(self.parent, "Aliases", str(result))

    def selectAvatar(self):
        avatarSelection = AvatarWidget(self.chat_widget.client, self.user.name, personal=True)
        avatarSelection.exec_()

    def addAvatar(self):
        avatarSelection = AvatarWidget(self.chat_widget.client, self.user.name)
        avatarSelection.exec_()

    def kick(self):
        pass

    def doubleClicked(self, item):
        # filter yourself
        if self._me.player is not None:
            if self._me.player.login == self.user.name:
                return
        # Chatter name clicked
        if item == self:
            self.chat_widget.openQuery(self.user, activate=True)  # open and activate query window

        elif item == self.statusItem:
            self._interactWithGame()

    def _interactWithGame(self):
        game = self.user_game
        if game is None or game.closed():
            return

        url = game.url(self.user_player.id)
        if game.state == GameState.OPEN:
            self.joinInGame(url)
        elif game.state == GameState.PLAYING:
            self.viewReplay(url)

    def pressed(self, item):
        menu = QtWidgets.QMenu(self.parent)

        def menu_add(action_str, action_connect, separator=False):
            if separator:
                menu.addSeparator()
            action = QtWidgets.QAction(action_str, menu)
            action.triggered.connect(action_connect)  # Triggers
            menu.addAction(action)

        player = self.user_player
        game = self.user_game
        _id, name = self._getIdName()

        if player is None or self._me.player is None:
            is_me = False
        else:
            is_me = player.id == self._me.player.id

        # only for us. Either way, it will display our avatar, not anyone avatar.
        if is_me:
            menu_add("Select Avatar", self.selectAvatar)

        # power menu
        if self.chat_widget.client.power > 1:
            # admin and mod menus
            menu_add("Assign avatar", self.addAvatar, True)

            if self.chat_widget.client.power == 2:

                def send_the_orcs():
                    route = Settings.get('mordor/host')
                    if _id != -1:
                        QtGui.QDesktopServices.openUrl(QUrl("{}/users/{}".format(route, _id)))
                    else:
                        QtGui.QDesktopServices.openUrl(QUrl("{}/users/{}".format(route, name)))

                menu_add("Send the Orcs", send_the_orcs, True)
                menu_add("Close Game", lambda: self.chat_widget.client.closeFA(name))
                menu_add("Close FAF Client", lambda: self.chat_widget.client.closeLobby(name))

        # Aliases link
        menu_add("View Aliases", self.viewAliases, True)

        # Don't allow self to be invited to a game, or join one
        if game is not None and not is_me:
            if game.state == GameState.OPEN:
                menu_add("Join hosted Game", self._interactWithGame, True)
            elif game.state == GameState.PLAYING:
                time_running = time.time() - game.launched_at
                if time_running > 5 * 60:
                    time_format = '%M:%S' if time_running < 60 * 60 else '%H:%M:%S'
                    duration_str = time.strftime(time_format, time.gmtime(time_running))
                    action_str = "View Live Replay (runs " + duration_str + ")"
                else:
                    wait_str = time.strftime('%M:%S', time.gmtime(5 * 60 - time_running))
                    action_str = "WAIT " + wait_str + " to view Live Replay"
                menu_add(action_str, self._interactWithGame, True)

        # Replays in vault
        if player is not None:  # not for irc user
            menu_add("View Replays in Vault", self.viewVaultReplay, True)

        # Friends and Foes Lists
        def player_or_irc_action(f, irc_f):
            _id, name = self._getIdName()
            if player is not None:
                return lambda: f(_id)
            else:
                return lambda: irc_f(name)

        cl = self.chat_widget.client
        me = self._me
        if is_me:  # We're ourselves
            pass
        elif me.isFriend(_id, name):  # We're a friend
            menu_add("Remove friend", player_or_irc_action(cl.remFriend, me.remIrcFriend), True)
        elif me.isFoe(_id, name):  # We're a foe
            menu_add("Remove foe", player_or_irc_action(cl.remFoe, me.remIrcFoe), True)
        else:  # We're neither
            menu_add("Add friend", player_or_irc_action(cl.addFriend, me.addIrcFriend), True)
            # FIXME - chatwidget sets mod status very inconsistently
            if self.modElevation() is None:  # so disable foeing mods for now
                menu_add("Add foe", player_or_irc_action(cl.addFoe, me.addIrcFoe))

        # Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())

    def viewVaultReplay(self):
        """ see the player replays in the vault """
        self.chat_widget.client.replays.setCurrentIndex(2)  # focus on Online Fault
        replayHandler = self.chat_widget.client.replays.vaultManager
        replayHandler.searchVault(-1400, "", self.user.name, 0)
        self.chat_widget.client.mainTabs.setCurrentIndex(self.chat_widget.client.mainTabs.indexOf(self.chat_widget.client.replaysTab))

    def joinInGame(self, url):
        client.instance.joinGameFromURL(url)

    def viewReplay(self, url):
        replay(url)
