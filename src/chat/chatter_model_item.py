from urllib import parse

from PyQt5.QtCore import QObject, pyqtSignal

from downloadManager import DownloadRequest
from fa import maps


class ChatterModelItem(QObject):
    """
    UI representation of a chatter.
    """
    updated = pyqtSignal(object)

    def __init__(self, cc, map_preview_dler, avatar_dler, relation_trackers):
        QObject.__init__(self)

        self._preview_dler = map_preview_dler
        self._avatar_dler = avatar_dler
        self._relation = relation_trackers

        self._player = None
        self._player_rel = None
        self._game = None
        self.cc = cc

        self.cc.updated.connect(self._updated)
        self.chatter.updated.connect(self._updated)
        self.chatter.newPlayer.connect(self._set_player)
        self._chatter_rel = self._relation.chatters[self.chatter.id_key]
        self._chatter_rel.updated.connect(self._updated)

        self._map_request = DownloadRequest()
        self._map_request.done.connect(self._updated)
        self._avatar_request = DownloadRequest()
        self._avatar_request.done.connect(self._updated)

        self.player = self.chatter.player

    @classmethod
    def builder(cls, map_preview_dler, avatar_dler, relation_trackers,
                **kwargs):
        def make(cc):
            return cls(cc, map_preview_dler, avatar_dler, relation_trackers)
        return make

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
            self._player_rel.updated.disconnect(self._updated)
            self._player_rel = None

        self._player = value

        if self._player is not None:
            self._player.updated.connect(self._at_player_updated)
            self._player.newCurrentGame.connect(self._set_game)
            self._player_rel = self._relation.players[self._player.id_key]
            self._player_rel.updated.connect(self._updated)
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
        name = self.map_name()
        if name is None:
            return
        if not maps.preview(name):
            self._preview_dler.download_preview(name, self._map_request)

    def map_name(self):
        game = self.game
        if game is None or game.closed() or game.mapname is None:
            return None
        return self.game.mapname.lower()

    def _download_avatar_if_needed(self):
        avatar_url = self.avatar_url()
        if avatar_url is None:
            return
        if avatar_url in self._avatar_dler.avatars:
            return
        self._avatar_dler.download_avatar(avatar_url, self._avatar_request)

    def avatar_url(self):
        try:
            url = self.player.avatar["url"]
        except (TypeError, AttributeError, KeyError):
            return None
        return parse.unquote(url)
