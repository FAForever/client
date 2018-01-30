from PyQt5.QtCore import pyqtSignal
from decorators import with_logger

from model.qobjectmapping import QObjectMapping
from model import game
from model.transaction import transactional


@with_logger
class Gameset(QObjectMapping):
    """
    Keeps track of currently active games. Removes games that closed. Reports
    creation and state change of games. Gives access to active games.

    Note that it doesn't remember which games ended - the server may choose to
    send a game state for a uid, send a state that closes it, then send a state
    with the same uid again, and it will be reported as a new game.
    """
    before_added = pyqtSignal(object, object)
    before_removed = pyqtSignal(object, object)
    added = pyqtSignal(object)
    removed = pyqtSignal(object)

    newLobby = pyqtSignal(object)
    newLiveGame = pyqtSignal(object)
    newClosedGame = pyqtSignal(object)
    newLiveReplay = pyqtSignal(object)

    def __init__(self, playerset):
        QObjectMapping.__init__(self)
        self._items = {}
        self._playerset = playerset

    def __getitem__(self, uid):
        return self._items[uid]

    def __iter__(self):
        return iter(self._items)

    @transactional
    def set_item(self, key, value, _transaction=None):
        if not isinstance(key, int) or not isinstance(value, game.Game):
            raise TypeError

        if key in self or value.closed():
            raise ValueError

        if key != value.id_key:
            raise ValueError

        self._items[key] = value
        value.before_updated.connect(self._at_game_update)
        value.before_replay_available.connect(self._at_live_replay)
        self._at_game_update(value, None, _transaction)
        self._logger.debug("Added game, uid {}".format(value.id_key))
        _transaction.emit(self.added, value)
        self.before_added.emit(value, _transaction)

    def __setitem__(self, key, value):
        # CAVEAT: use only as an entry point for model changes.
        self.set_item(key, value)

    @transactional
    def clear(self, _transaction=None):
        # Abort_game removes g from dict, so 'for g in values()' complains
        for g in list(self._items.values()):
            g.abort_game(_transaction)

    def _at_game_update(self, new, old, _transaction=None):
        if new.closed():
            self.del_item(new.id_key, _transaction)
        if old is None or new.state != old.state:
            self._new_state(new, _transaction)

    def _new_state(self, g, _transaction=None):
        self._logger.debug("New game state {}, uid {}".format(g.state,
                                                              g.id_key))
        if g.state == game.GameState.OPEN:
            _transaction.emit(self.newLobby, g)
        elif g.state == game.GameState.PLAYING:
            _transaction.emit(self.newLiveGame, g)
        elif g.state == game.GameState.CLOSED:
            _transaction.emit(self.newClosedGame, g)

    def _at_live_replay(self, game, _transaction=None):
        _transaction.emit(self.newLiveReplay, game)

    def __delitem__(self, uid):
        # CAVEAT: use only as an entry point for model changes.
        self.del_item(uid)

    @transactional
    def del_item(self, uid, _transaction=None):
        try:
            g = self._items[uid]
            g.before_updated.disconnect(self._at_game_update)
            g.before_replay_available.disconnect(self._at_live_replay)
            del self._items[g.id_key]
            self._logger.debug("Removed game, uid {}".format(g.id_key))
            _transaction.emit(self.removed, g)
            self.before_removed.emit(g, _transaction)
        except KeyError:
            pass


class PlayerGameIndex:
    # Helper class that keeps track of player / game relationship and helps
    # assign games to players that reconnected.
    def __init__(self, gameset, playerset):
        self._playerset = playerset
        self._gameset = gameset
        self._playerset.before_added.connect(self._on_player_added)
        self._playerset.before_removed.connect(self._on_player_removed)
        self._gameset.before_added.connect(self._on_game_added)
        self._gameset.before_removed.connect(self._on_game_removed)

        self._idx = {}

    def player_game(self, pname):
        return self._idx.get(pname)

    def _on_game_added(self, game, _transaction=None):
        game.before_updated.connect(self._at_game_update)
        for p in game.players:
            self._set_relation(p, game, _transaction)

    def _on_game_removed(self, game, _transaction=None):
        game.before_updated.disconnect(self._at_game_update)
        for p in game.players:
            self._remove_relation(p, game, _transaction)

    def _at_game_update(self, new, old, _transaction=None):
        news = set() if new.closed() else set(new.players)
        olds = set() if old.closed() else set(old.players)
        removed = olds - news
        added = news - olds
        for p in removed:
            self._remove_relation(p, new, _transaction)
        for p in added:
            self._set_relation(p, new, _transaction)

    def _remove_relation(self, pname, game, _transaction=None):
        if pname not in self._idx:
            return
        if self.player_game(pname) != game:
            return

        player = self._playerset.get(pname)
        del self._idx[pname]

        if player is not None:
            player.set_currentGame(None, _transaction)
            game.ingame_player_removed(player, _transaction)

    def _set_relation(self, pname, game, _transaction=None):
        oldgame = self.player_game(pname)
        if not self._player_did_change_game(game, oldgame):
            return

        player = self._playerset.get(pname)
        self._idx[pname] = game

        if player is not None:
            player.set_currentGame(game, _transaction)
            if oldgame is not None:
                oldgame.ingame_player_removed(player, _transaction)
            game.ingame_player_added(player, _transaction)

    def _player_did_change_game(self, new, old):
        # Removing or setting new game should always happen
        if new is None or old is None:
            return True

        if new.id_key == old.id_key:
            return False

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

    def _on_player_added(self, player, _transaction=None):
        pgame = self.player_game(player.login)
        if pgame is not None:
            player.set_currentGame(pgame, _transaction)
            pgame.ingame_player_added(player, _transaction)

    def _on_player_removed(self, player, _transaction=None):
        pgame = self.player_game(player.login)
        if pgame is not None:
            pgame.ingame_player_removed(player, _transaction)
