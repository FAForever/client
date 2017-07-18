from PyQt5.QtCore import QObject, pyqtSignal

import client

from model.player import Player
from model.game import GameState


class Playerset(QObject):
    """
    Wrapper for an id->Player map

    Used to lookup players either by id (cheap) or by login (expensive, don't do this).
    """
    playersUpdated = pyqtSignal(list)

    def __init__(self, user, gameset):
        QObject.__init__(self)
        self.user = user
        self.coloredNicknames = False
        self.gameset = gameset
        self.gameset.newGame.connect(self._onNewGame)

        # UID -> Player map
        self._players = {}
        # Login -> Player map
        self._logins = {}

    def isPlayer(self, name):
        """
        Convenience function for other modules to inquire about a user's civilian status.
        """
        return name in self

    def keys(self):
        return list(self._players.keys())

    def values(self):
        return list(self._players.values())

    def items(self):
        return list(self._players.items())

    def get(self, item, default):
        val = self.__getitem__(item)
        return val if val else default

    def getID(self, name):
        if name in self._logins:
            return self._logins[name].id
        return -1

    def __contains__(self, item):
        return self.__getitem__(item) is not None

    def __getitem__(self, item):
        if isinstance(item, Player):
            return item
        if isinstance(item, int) and item in self._players:
            return self._players[item]
        if item in self._logins:
                return self._logins[item]

    def __setitem__(self, key, value):
        assert isinstance(key, int)
        self._players[key] = value
        self._logins[value.login] = value

    def clear(self):
        oldplayers = self.keys()
        self.playersUpdated.emit(oldplayers)
        self._players = {}
        self._logins = {}

    def _onNewGame(self, game):
        game.playersUpdated.connect(self._onPlayersUpdate)
        self._onPlayersUpdate(game, [])

    def _onPlayersUpdate(self, game, old):
        old = [self[name] for name in old if name in self]
        new = [self[name] for name in game.players if name in self]

        for player in old:
            if player.login in client.instance.urls:
                del client.instance.urls[player.login]

        if game.state == GameState.CLOSED:
            game.playersUpdated.disconnect(self._onPlayersUpdate)
        else:
            for player in new:
                client.instance.urls[player.login] = game.url(player.id)

        playersum = list(set(old + new))
        self.playersUpdated.emit(playersum)
