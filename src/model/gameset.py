from PyQt5.QtCore import QObject, pyqtSignal
from decorators import with_logger

from model import game

"""
Keeps track of currently active games. Passes game state messages to correct
games or creates them if there's no game with a given uid. Removes games that
closed. Reports creation and state change of games. Gives access to active games.

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

    def update_set(self, message):
        if "uid" not in message:
            self._logger.warn("No uid in game info message")
            return

        uid = message["uid"]
        if uid not in self.games:
            self._add_game(message)
        else:
            g = self.games[uid]
            self._update_game(g, message)

    def clear_set(self):
        # Abort_game removes g from dict, so 'for g in values()' complains
        for g in list(self.games.values()):
            g.abort_game()

    def _add_game(self, message):
        try:
            g = game.Game(**message)
            if g.closed():  # Don't register an already closed game
                return
        except game.BadUpdateException as e:
            self._logger.warn("Bad game info update: " + e.args[0])
            return

        self.games[g.uid] = g
        g.newState.connect(lambda: self._new_state(g))
        self._new_state(g)   # new_state reports new games of given state, so let's report
        g.gameClosed.connect(lambda: self._remove_game(g))
        self.newGame.emit(g)

        self._logger.debug("Added game, uid {}".format(g.uid))

    def _update_game(self, g, message):
        try:
            g.update(**message)
        except game.BadUpdateException as e:
            self._logger.warn("Bad game info update: " + e.args[0])
            g.abort_game()

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
            del self.games[g.uid]
            self._logger.debug("Removed game, uid {}".format(g.uid))
        except KeyError:    # Maybe we both aborted and closed the game?
            pass

    def __getitem__(self, uid):
        return self.games[uid]
    def __contains__(self, uid):
        return uid in self.games
    def __iter__(self):
        return self.games.values().__iter__()
