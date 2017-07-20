from PyQt5.QtCore import QObject, pyqtSignal

import client

from model.player import Player
from model.game import GameState


class Playerset(QObject):
    """
    Wrapper for an id->Player map

    Used to lookup players either by id or by login.
    """
    playersUpdated = pyqtSignal(list)
    playerAdded = pyqtSignal(object)
    playerRemoved = pyqtSignal(object)

    def __init__(self, gameset):
        QObject.__init__(self)
        self.gameset = gameset
        self.gameset.newGame.connect(self._onNewGame)

        # UID -> Player map
        self._players = {}
        # Login -> Player map
        self._logins = {}

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._players[item]
        if isinstance(item, str):
            return self._logins[item]
        raise TypeError

    def __len__(self):
        return len(self._players)

    def __iter__(self):
        return iter(self._players)

    # We need to define the below things - QObject
    # doesn't allow for Mapping mixin
    def keys(self):
        return self._players.keys()

    def values(self):
        return self._players.values()

    def items(self):
        return self._players.items()

    def get(self, item, default = None):
        try:
            return self[item]
        except KeyError:
            return default

    def __contains__(self, item):
        try:
            self[item]
            return True
        except KeyError:
            return False

    def getID(self, name):
        if name in self:
            return self[name].id
        return -1

    def __setitem__(self, key, value):
        if not isinstance(key, int) or not isinstance(value, Player):
            raise TypeError

        if key in self:     # disallow overwriting existing players
            raise ValueError

        self._players[key] = value
        self._logins[value.login] = value
        self.playerAdded.emit([value])

    def __delitem__(self, item):
        try:
            player = self[item]
        except KeyError:
            return
        del self._players[player.id]
        del self._players[player.login]
        self.playerRemoved.emit(player)

    def clear(self):
        oldplayers = self.keys()
        for player in oldplayers:
            self.playerRemoved.emit(player)
        self._players = {}
        self._logins = {}

    def _onNewGame(self, game):
        game.gameUpdated.connect(self._onGameUpdate)
        self._onGameUpdate(game, None)

    def _onGameUpdate(self, game, old):

        if old is None or set(game.players) != set(old.players):
            self._onNewTeams(game, game.players, [] if old is None else old.players)

        if game.state == GameState.CLOSED:
            game.gameUpdated.disconnect(self._onGameUpdate)

    def _onNewTeams(self, game, new, old):
        old = [self[name] for name in old if name in self]
        new = [self[name] for name in new if name in self]

        for player in old:
            if player.login in client.instance.urls:
                del client.instance.urls[player.login]
        if game.state != GameState.CLOSED:
            for player in new:
                client.instance.urls[player.login] = game.url(player.id)

        playersum = list(set(old + new))
        self.playersUpdated.emit(playersum)
