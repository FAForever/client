from PyQt5.QtCore import QObject, pyqtSignal
from decorators import with_logger

from model import game

"""
Keeps track of currently active games. Removes games that closed. Reports
creation and state change of games. Gives access to active games.

Note that it doesn't remember which games ended - the server may choose to
send a game state for a uid, send a state that closes it, then send a state
with the same uid again, and it will be reported as a new game.
"""


@with_logger
class Gameset(QObject):
    newGame = pyqtSignal(object)

    newLobby = pyqtSignal(object)
    newLiveGame = pyqtSignal(object)
    newClosedGame = pyqtSignal(object)

    def __init__(self):
        QObject.__init__(self)
        self.games = {}

    def __getitem__(self, uid):
        return self.games[uid]

    def __contains__(self, uid):
        return uid in self.games

    def __iter__(self):
        return iter(self.games)

    def keys(self):
        return self.games.keys()

    def values(self):
        return self.games.values()

    def items(self):
        return self.games.items()

    def get(self, item, default=None):
        try:
            return self[item]
        except KeyError:
            return default

    def __setitem__(self, key, value):
        if not isinstance(key, int) or not isinstance(value, game.Game):
            raise TypeError

        if key in self or value.closed():
            raise ValueError

        self.games[key] = value
        value.gameUpdated.connect(self._at_game_update)
        self._new_state(value)
        self.newGame.emit(value)
        self._logger.debug("Added game, uid {}".format(value.uid))

    def clear(self):
        # Abort_game removes g from dict, so 'for g in values()' complains
        for g in list(self.games.values()):
            g.abort_game()

    def _at_game_update(self, new, old):
        if new.state != old.state:
            self._new_state(new)
            if new.state == game.GameState.CLOSED:
                self._remove_game(new)

    def _new_state(self, g):
        self._logger.debug("New game state {}, uid {}".format(g.state, g.uid))
        if g.state == game.GameState.OPEN:
            self.newLobby.emit(g)
        elif g.state == game.GameState.PLAYING:
            self.newLiveGame.emit(g)
        elif g.state == game.GameState.CLOSED:
            self.newClosedGame.emit(g)

    def _remove_game(self, g):
        try:
            g = self.games[g.uid]
            g.gameUpdated.disconnect(self._at_game_update)
            del self.games[g.uid]
            self._logger.debug("Removed game, uid {}".format(g.uid))
        except KeyError:
            pass
