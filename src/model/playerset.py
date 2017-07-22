from PyQt5.QtCore import QObject, pyqtSignal

from model.player import Player


class Playerset(QObject):
    """
    Wrapper for an id->Player map

    Used to lookup players either by id or by login.
    """
    playersUpdated = pyqtSignal(list)
    playerAdded = pyqtSignal(object)
    playerRemoved = pyqtSignal(object)

    def __init__(self):
        QObject.__init__(self)

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

    def get(self, item, default=None):
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
        self.playerAdded.emit(value)
        value.updated.connect(self._at_player_updated)
        value.newCurrentGame.connect(self._at_player_updated)

    def __delitem__(self, item):
        try:
            player = self[item]
        except KeyError:
            return
        del self._players[player.id]
        del self._logins[player.login]
        player.updated.disconnect(self._at_player_updated)
        player.newCurrentGame.disconnect(self._at_player_updated)
        self.playerRemoved.emit(player)

    def _at_player_updated(self, player):
        self.playersUpdated.emit([player])

    def clear(self):
        oldplayers = list(self.keys())
        for player in oldplayers:
            del self[player]
