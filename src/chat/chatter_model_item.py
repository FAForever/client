from urllib import parse
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMenu, QAction
from downloadManager import DownloadRequest
from fa import maps
from model.game import GameState


class ChatterModelItem(QObject):
    """
    UI representation of a chatter.
    """
    updated = pyqtSignal(object)

    def __init__(self, cc, preview_dler, avatar_dler):
        QObject.__init__(self)

        self._player = None
        self._game = None
        self.cc = cc
        self.chatter.updated.connect(self._updated)
        self.chatter.newPlayer.connect(self._set_player)

        self._preview_dler = preview_dler
        self._avatar_dler = avatar_dler
        self._map_request = DownloadRequest()
        self._map_request.done.connect(self._updated)
        self._avatar_request = DownloadRequest()
        self._avatar_request.done.connect(self._updated)

        self.player = self.chatter.player

    def _updated(self):
        self.updated.emit(self)

    @property
    def chatter(self):
        return self.cc.chatter

    def _set_player(self, chatter, new_player, old_player):
        self.player = new_player
        self._updated()

    @property
    def player(self):
        return self._player

    @player.setter
    def player(self, value):
        if self._player is not None:
            self.game = None
            self._player.updated.disconnect(self._at_player_updated)
            self._player.newCurrentGame.disconnect(self._set_game)

        self._player = value

        if self._player is not None:
            self._player.updated.connect(self._at_player_updated)
            self._player.newCurrentGame.connect(self._set_game)
            self.game = self._player.currentGame
            self._download_avatar_if_needed()

    def _at_player_updated(self):
        self._download_avatar_if_needed()
        self._updated()

    def _set_game(self, player, game):
        self.game = game
        self._updated()

    @property
    def game(self):
        return self._game

    @game.setter
    def game(self, value):
        if self._game is not None:
            self._game.updated.disconnect(self._at_game_updated)
            self._game.liveReplayAvailable.disconnect(self._updated)

        self._game = value

        if self._game is not None:
            self._game.updated.connect(self._at_game_updated)
            self._game.liveReplayAvailable.connect(self._updated)
            self._download_map_preview_if_needed()

    def _at_game_updated(self, new, old):
        if new.mapname != old.mapname:
            self._download_map_preview_if_needed()
        self._updated()

    def _download_map_preview_if_needed(self):
        name = self._map_name()
        if name is None:
            return
        if not maps.preview(name):
            self._preview_dler.download_preview(name, self._map_request)

    def _map_name(self):
        game = self.game
        if game is None or game.closed() or game.mapname is None:
            return None
        return self.game.mapname.lower()

    def map_icon(self):
        name = self._map_name()
        return None if name is None else maps.preview(name)

    def chatter_status(self):
        game = self.game
        if game is None or game.closed():
            return "none"
        if game.state == GameState.OPEN:
            if game.host == self.chatter.name:
                return "host"
            return "lobby"
        if game.state == GameState.PLAYING:
            if game.has_live_replay:
                return "playing"
            return "playing5"
        return "unknown"

    def chatter_rank(self):
        try:
            return self.player.league["league"]
        except (TypeError, AttributeError, KeyError):
            return "civilian"

    def _download_avatar_if_needed(self):
        avatar_url = self._avatar_url()
        if avatar_url is None:
            return
        if avatar_url in self._avatar_dler.avatars:
            return
        self._avatar_dler.download_avatar(avatar_url, self._avatar_request)

    def _avatar_url(self):
        try:
            url = self.player.avatar["url"]
        except (TypeError, AttributeError, KeyError):
            return None
        return parse.unquote(url)

    def chatter_avatar_icon(self):
        avatar_url = self._avatar_url()
        if avatar_url is None:
            return None
        if avatar_url not in self._avatar_dler.avatars:
            return
        return QIcon(self._avatar_dler.avatars[avatar_url])

    def chatter_country(self):
        if self.player is None:
            return '__'
        country = self.player.country
        if country is None or country == '':
            return '__'
        return country

    def rank_tooltip(self):
        if self.player is None:
            return "IRC User"
        player = self.player
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
        if league is not None and "division" in league:
            tooltip_str = "Division : {}\n{}".format(league["division"],
                                                     tooltip_str)
        return tooltip_str

    def status_tooltip(self):
        # Status tooltip handling
        game = self.game
        if game is None or game.closed():
            return "Idle"

        private_str = " (private)" if game.password_protected else ""
        if game.state == GameState.PLAYING and not game.has_live_replay:
            delay_str = " - LIVE DELAY (5 Min)"
        else:
            delay_str = ""

        head_str = ""
        if game.state == GameState.OPEN:
            if game.host == self.player.login:
                head_str = "Hosting{private} game</b>"
            else:
                head_str = "In{private} Lobby</b> (host {host})"
        elif game.state == GameState.PLAYING:
            head_str = "Playing</b>{delay}"
        header = head_str.format(private=private_str, delay=delay_str,
                                 host=game.host)

        formatting = ("<b>{}<br/>"
                      "title: {}<br/>"
                      "mod: {}<br/>"
                      "map: {}<br/>"
                      "players: {} / {}<br/>"
                      "id: {}")

        game_str = formatting.format(header, game.title, game.featured_mod,
                                     game.mapdisplayname, game.num_players,
                                     game.max_players, game.uid)
        return game_str

    def avatar_tooltip(self):
        try:
            return self.player.avatar["tooltip"]
        except (TypeError, AttributeError, KeyError):
            return None

    def map_tooltip(self):
        if self.game is None:
            return None
        return self.game.mapdisplayname

    def country_tooltip(self):
        return self.chatter_country()

    def nick_tooltip(self):
        return self._country_tooltip()

    def context_menu(self):
        return ChatterContextMenu(self, self.chatter, self.player, self.game)


class ChatterContextMenu(QMenu):
    def __init__(self, parent, chatter, player, game):
        QMenu.__init__(self, parent)
        self.chatter = chatter
        self.player = player
        self.game = game
        self._init_entries()

    # TODO - add mod entries
    # TODO - add entries for me
    # TODO - friend entries
    def _init_entries(self):
        if self.chatter is not None:
            self._init_chatter_entries()
        if self.player is not None:
            self.add_seperator()
            self._init_player_entries()
        if self.game is not None:
            self.add_separator()
            self._init_game_entries()

    def _init_chatter_entries(self):
        pass

    def _init_player_entries(self):
        pass

    def _init_game_entries(self):
        pass

    def _add_menu(self, name, callback):
        action = QAction(name, self)
        action.triggered.connect(callback)
        self.addAction(action)
