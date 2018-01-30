from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QNetworkRequest
from chat._avatarWidget import AvatarWidget
import time
from urllib import parse

from fa.replay import replay
from fa import maps

import util
from config import Settings

from model.game import GameState
from client.aliasviewer import AliasWindow
from chat.gameinfo import SensitiveMapInfoChecker
from downloadManager import PreviewDownloadRequest

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
        self._me.relationsUpdated.connect(self._check_player_relation)
        self._me.ircRelationsUpdated.connect(self._check_user_relation)

        self._map_dl_request = PreviewDownloadRequest()
        self._map_dl_request.done.connect(self._on_map_downloaded)

        self._aliases = AliasWindow(self.parent)
        self._game_info_hider = SensitiveMapInfoChecker(self._me)

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
            self._user.updated.disconnect(self.update_user)
            self._user.newPlayer.disconnect(self._set_user_player)

        self._user = value
        self.update_user()

        if self._user is not None:
            self._user.updated.connect(self.update_user)
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
            self._user_player.updated.disconnect(self.update_player)
            self._user_player.newCurrentGame.disconnect(self._set_user_game)

        self._user_player = value
        self.update_player()

        if self._user_player is not None:
            self._user_player.updated.connect(self.update_player)
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
            self._user_game.updated.disconnect(self.update_game)
            self._user_game.liveReplayAvailable.disconnect(self.update_game)

        self._user_game = value
        self.update_game()

        if self._user_game is not None:
            self._user_game.updated.connect(self.update_game)
            self._user_game.liveReplayAvailable.connect(self.update_game)

    def _check_player_relation(self, players):
        if self.user_player is None:
            return

        if self.user_player.id in players:
            self.set_color()
            self._verify_sort_order()

    def _check_user_relation(self, users):
        if self.user.name in users:
            self.set_color()
            self._verify_sort_order()

    def is_filtered(self, _filter):
        clan = None if self.user_player is None else self.user_player.clan
        clan = clan if clan is not None else ""
        name = self.user.name
        if _filter in clan.lower() or _filter in name.lower():
            return True
        return False

    def set_visible(self, visible):
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

        if self._me.login is not None:
            if self.user.name == self._me.login:
                return True
            if other.user.name == self._me.login:
                return False

        # if not same rank sort
        if self_rank != other_rank:
            return self_rank < other_rank

        # Default: Alphabetical
        return self.user.name.lower() < other.user.name.lower()

    def _verify_sort_order(self):
        if self.row() != -1:
            self.channel.verify_sort_order(self)

    def _get_id_name(self):
        _id = -1 if self.user_player is None else self.user_player.id
        name = self.user.name
        return _id, name

    def get_user_rank(self, user):
        # TODO: Add subdivision for admin?
        me = self._me
        _id, name = user._get_id_name()
        if user.mod_elevation():
            return self.RANK_ELEVATION
        if me.isFriend(_id, name):
            return self.RANK_FRIEND - (2 if self.chat_widget.client.friendsontop else 0)
        if me.isFoe(_id, name):
            return self.RANK_FOE
        if user.user_player is not None:
            return self.RANK_USER

        return self.RANK_NONPLAYER

    def mod_elevation(self):
        if not self.user.is_mod(self.channel.name):
            return None
        return self.user.elevation[self.channel.name]

    def update_avatar(self):
        # FIXME: prodding the underlying C++ object to see if it exists
        # Needed if we're gone while downloading our avatar
        # We don't subclass QObject, so we have to do it this way
        try:
            self.isSelected()
        except RuntimeError:
            return
        try:
            avatar = self.user_player.avatar
        except AttributeError:
            avatar = None

        if avatar is not None:
            self.avatarTip = avatar["tooltip"]
            url = parse.unquote(avatar["url"])
            avatarPix = util.respix(url)

            if avatarPix:
                self.avatarItem.setIcon(QtGui.QIcon(avatarPix))
                self.avatarItem.setToolTip(self.avatarTip)
            else:
                if util.addcurDownloadAvatar(url, self):
                    self.chat_widget.nam.get(QNetworkRequest(QUrl(url)))
        else:
            # No avatar set.
            self.avatarItem.setIcon(QtGui.QIcon())
            self.avatarItem.setToolTip(None)

    def set_chatter_name(self):
        if self.user_player is not None and self.user_player.clan is not None:
            self.setText("[{}]{}".format(self.user_player.clan,
                                         self.user.name))
        else:
            self.setText(self.user.name)

    def update_user(self):
        self.set_chatter_name()
        self.set_color()
        self._verify_sort_order()

    def update_player(self):
        self.set_chatter_name()
        self.update_rank()
        self.update_country()
        self.update_avatar()

    def update_country(self):
        player = self.user_player
        if player is None:
            self.setIcon(QtGui.QIcon())
            self.setToolTip("")
            return
        # server sends '' for no ip2country-resolution
        if player.country is None or player.country == '':
            country = '__'
        else:
            country = player.country
        self.setIcon(util.THEME.icon("chat/countries/{}.png".format(country.lower())))
        self.setToolTip(country)

    def update_rank(self):
        player = self.user_player
        if player is None:
            self.rankItem.setIcon(util.THEME.icon("chat/rank/civilian.png"))
            self.rankItem.setToolTip("IRC User")
            return
        # chr(0xB1) = +-
        formatting = ("Global Rating: {} ({} Games) [{}\xb1{}]\n"
                      "Ladder Rating: {} [{}\xb1{}]")
        tooltip_str = formatting.format((int(player.rating_estimate())),
                                        player.number_of_games,
                                        int(player.rating_mean),
                                        int(player.rating_deviation),
                                        int(player.ladder_estimate()),
                                        int(player.ladder_rating_mean),
                                        int(player.ladder_rating_deviation))
        league = player.league
        if league is not None:
            icon_str = league["league"]
            tooltip_str = "Division : {}\n{}".format(league["division"],
                                                     tooltip_str)
        else:
            icon_str = "newplayer"
        self.rankItem.setIcon(util.THEME.icon("chat/rank/{}.png".format(icon_str)))
        self.rankItem.setToolTip(tooltip_str)

    def update_game(self):
        self.update_status_tooltip()
        self.update_status_icon()
        self.update_map()

    def update_status_tooltip(self):
        # Status tooltip handling
        game = self.user_game
        should_hide_info = self._game_info_hider.has_sensitive_data(game)
        if game is not None and not game.closed():
            if should_hide_info:
                game_map = "<i>[delayed reveal]</i>"
                game_title = "<i>[delayed reveal]</i>"
            else:
                game_map = game.mapdisplayname
                game_title = game.title
            private_str = " (private)" if game.password_protected else ""
            delay_str = ""
            if game.state == GameState.OPEN:
                if game.host == self.user.name:
                    head_str = "Hosting{private} game</b>"
                else:
                    head_str = "In{private} Lobby</b> (host {host})"
            elif game.state == GameState.PLAYING:
                head_str = "Playing</b>{delay}"
                if not game.has_live_replay:
                    delay_str = " - LIVE DELAY (5 Min)"
            else:  # game.state == something else
                head_str = "Playing maybe ...</b>"
            formatting = "<b>{}<br/>title: {}<br/>mod: {}<br/>map: {}<br/>players: {} / {}<br/>id: {}"
            game_str = formatting.format(head_str.format(private=private_str, delay=delay_str, host=game.host),
                                         game_title, game.featured_mod, game_map,
                                         game.num_players, game.max_players, game.uid)
        else:  # game is None or closed
            game_str = "Idle"

        self.statusItem.setToolTip(game_str)

    def update_status_icon(self):
        # Status icon handling
        game = self.user_game
        if game is not None and not game.closed():
            if game.state == GameState.OPEN:
                if game.host == self.user.name:
                    icon_str = "host"
                else:
                    icon_str = "lobby"
            elif game.state == GameState.PLAYING:
                if game.has_live_replay:
                    icon_str = "playing"
                else:
                    icon_str = "playing5"
            else:  # game.state == something else
                icon_str = "unknown"
        else:  # game is None or closed
            icon_str = "none"

        self.statusItem.setIcon(util.THEME.icon("chat/status/%s.png" % icon_str))

    def update_map(self):
        # Map icon handling - if we're in game, show the map if toggled on
        game = self.user_game
        should_hide_info = self._game_info_hider.has_sensitive_data(game)
        if game is not None and not game.closed() and util.settings.value("chat/chatmaps", False):
            if should_hide_info:
                self.mapItem.setIcon(util.THEME.icon("chat/status/unknown.png"))
                self.mapItem.setToolTip("<i>[delayed reveal]</i>")
            else:
                mapname = game.mapname
                icon = maps.preview(mapname)
                if not icon:
                    dler = self.chat_widget.client.map_downloader
                    dler.download_preview(mapname, self._map_dl_request)
                else:
                    self.mapItem.setIcon(icon)

                self.mapItem.setToolTip(game.mapdisplayname)
        else:
            self.mapItem.setIcon(QtGui.QIcon())
            self.mapItem.setToolTip("")

    def _on_map_downloaded(self, mapname, result):
        if self.user_game is None or self.user_game.mapname != mapname:
            return
        path, is_local = result
        self.mapItem.setIcon(util.THEME.icon(path, is_local))

    def update(self):
        self.update_user()
        self.update_player()
        self.update_game()

    def set_color(self):
        # FIXME - we should really get colors in the constructor
        pcolors = self.chat_widget.client.player_colors
        elevation = self.mod_elevation()
        _id, name = self._get_id_name()
        if elevation is not None:
            color = pcolors.getModColor(elevation, _id, name)
        else:
            color = pcolors.getUserColor(_id, name)
        self.setForeground(QtGui.QColor(color))

    def view_aliases(self):
        if self.user_player is not None:
            player_id = self.user_player.id
        else:
            player_id = None
        self._aliases.view_aliases(self.user.name, player_id)

    def select_avatar(self):
        avatarSelection = AvatarWidget(self.chat_widget.client, self.user.name, personal=True)
        avatarSelection.exec_()

    def add_avatar(self):
        avatarSelection = AvatarWidget(self.chat_widget.client, self.user.name)
        avatarSelection.exec_()

    def kick(self):
        pass

    def double_clicked(self, item):
        # filter yourself
        if self._me.login is not None:
            if self._me.login == self.user.name:
                return
        # Chatter name clicked
        if item == self:
            self.chat_widget.open_query(self.user, activate=True)  # open and activate query window

        elif item == self.statusItem:
            self._interact_with_game()

    def _interact_with_game(self):
        game = self.user_game
        if game is None or game.closed():
            return

        url = game.url(self.user_player.id)
        if game.state == GameState.OPEN:
            self.join_in_game(url)
        elif game.state == GameState.PLAYING:
            self.view_replay(url)

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
        _id, name = self._get_id_name()

        if player is None or self._me.player is None:
            is_me = False
        else:
            is_me = player.id == self._me.player.id

        if is_me:  # only for us. Either way, it will display our avatar, not anyone avatar.
            menu_add("Select Avatar", self.select_avatar)

        # power menu
        if self.chat_widget.client.power > 1:
            # admin and mod menus
            menu_add("Assign avatar", self.add_avatar, True)

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

        menu_add("View Aliases", self.view_aliases, True)
        if player is not None:  # not for irc user
            if int(player.ladder_estimate()) != 0:  # not for 'never played ladder'
                menu_add("View in Leaderboards", self.view_in_leaderboards)

        # Don't allow self to be invited to a game, or join one
        if game is not None and not is_me:
            if game.state == GameState.OPEN:
                menu_add("Join hosted Game", self._interact_with_game, True)
            elif game.state == GameState.PLAYING:
                time_running = time.time() - game.launched_at
                if game.has_live_replay:
                    time_format = '%M:%S' if time_running < 60 * 60 else '%H:%M:%S'
                    duration_str = time.strftime(time_format, time.gmtime(time_running))
                    action_str = "View Live Replay (runs " + duration_str + ")"
                else:
                    wait_str = time.strftime('%M:%S', time.gmtime(game.LIVE_REPLAY_DELAY_SECS - time_running))
                    action_str = "WAIT " + wait_str + " to view Live Replay"
                menu_add(action_str, self._interact_with_game, True)

        if player is not None:  # not for irc user
            menu_add("View Replays in Vault", self.view_vault_replay, True)

        # Friends and Foes Lists
        def player_or_irc_action(f, irc_f):
            _id, name = self._get_id_name()
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
            if self.mod_elevation() is None:  # so disable foeing mods for now
                menu_add("Add foe", player_or_irc_action(cl.addFoe, me.addIrcFoe))

        # Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())

    def view_vault_replay(self):
        self.chat_widget.client.searchUserReplays(self.user.name)

    def join_in_game(self, url):
        self.chat_widget.client.joinGameFromURL(url)

    def view_replay(self, url):
        replay(url)

    def view_in_leaderboards(self):
        self.chat_widget.client.viewUserLeaderboards(self.user_player)
