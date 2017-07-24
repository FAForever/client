from PyQt5.QtCore import QObject, pyqtSignal
from decorators import with_logger

from model import game


@with_logger
class Gameset(QObject):
    """
    Keeps track of currently active games. Removes games that closed. Reports
    creation and state change of games. Gives access to active games.

    Note that it doesn't remember which games ended - the server may choose to
    send a game state for a uid, send a state that closes it, then send a state
    with the same uid again, and it will be reported as a new game.
    """
    newGame = pyqtSignal(object)

    newLobby = pyqtSignal(object)
    newLiveGame = pyqtSignal(object)
    newClosedGame = pyqtSignal(object)

    def __init__(self, playerset):
        QObject.__init__(self)
        self.games = {}
        self._playerset = playerset
        self._idx = PlayerGameIndex(playerset)

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

        if key != value.uid:
            raise ValueError

        self.games[key] = value
        # We should be the first ones to connect to the signal
        value.gameUpdated.connect(self._at_game_update)
        self._at_game_update(value, None)
        self.newGame.emit(value)
        self._logger.debug("Added game, uid {}".format(value.uid))

    def clear(self):
        # Abort_game removes g from dict, so 'for g in values()' complains
        for g in list(self.games.values()):
            g.abort_game()

    def _at_game_update(self, new, old):
        if new.closed():
            self._remove_game(new)
        self._idx.at_game_update(new, old)
        if old is None or new.state != old.state:
            self._new_state(new)

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


class PlayerGameIndex:
    # Helper class that keeps track of player / game relationship and helps
    # assign games to players that reconnected.
    def __init__(self, playerset):
        self._playerset = playerset
        self._idx = {}
        self._playerset.playerAdded.connect(self._on_player_added)
        self._playerset.playerRemoved.connect(self._on_player_removed)

    # Called by gameset
    def at_game_update(self, new, old):
        old_closed = old is None or old.closed()

        news = set() if new.closed() else set(new.players)
        olds = set() if old_closed else set(old.players)

        removed = [p for p in olds - news
                   if p in self._idx and self._idx[p] == new]
        added = news - olds

        # Player games are part of state, so update all first before signals
        signals = []
        for p in removed:
            signals.append(self._set_player_game_defer_signal(p, None))
        for p in added:
            signals.append(self._set_player_game_defer_signal(p, new))

        for s in signals:
            s()

    def _set_player_game_defer_signal(self, pname, game):
        oldgame = self._idx.get(pname)
        if not self._should_update_player_game(game, oldgame):
            return lambda: None

        if game is None:
            if pname in self._idx:
                del self._idx[pname]
        else:
            self._idx[pname] = game

        if pname in self._playerset:
            player = self._playerset[pname]
            return player.set_current_game_defer_signal(game)
        else:
            return lambda: None

    def _should_update_player_game(self, new, old):
        # Removing or setting new game should always happen
        if new is None or old is None:
            return True

        # Games should be not closed now
        # Lobbies always take precedence - if there are 2 at once, tough luck
        if new.state == game.GameState.OPEN:
            return True
        if old.state == game.GameState.OPEN:
            return False

        # Both games have started, pick later one
        if new.launched_at is None:
            return False
        if old.launched_at is None:
            return True
        return new.launched_at > old.launched_at

    def player_game(self, pname):
        return self._idx.get(pname)

    def _on_player_added(self, player):
        pgame = self.player_game(player.login)
        if pgame is not None:
            player.currentGame = pgame
            pgame.connectedPlayerAdded.emit(pgame, player)

    def _on_player_removed(self, player):
        pgame = self.player_game(player.login)
        if pgame is not None:
            pgame.connectedPlayerRemoved.emit(pgame, player)
