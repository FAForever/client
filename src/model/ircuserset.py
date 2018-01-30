from PyQt5.QtCore import pyqtSignal
from model.qobjectmapping import QObjectMapping
from model.transaction import transactional


class IrcUserset(QObjectMapping):
    added = pyqtSignal(object)
    removed = pyqtSignal(object)
    before_added = pyqtSignal(object, object)
    before_removed = pyqtSignal(object, object)

    def __init__(self, playerset):
        QObjectMapping.__init__(self)
        self._items = {}
        self._playerset = playerset
        playerset.before_added.connect(self._at_player_added)
        playerset.before_removed.connect(self._at_player_removed)

    def __getitem__(self, item):
        return self._items[item]

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    @transactional
    def set_item(self, key, value, _transaction=None):
        if key in self:     # disallow overwriting existing chatters
            raise ValueError

        if key != value.id_key:
            raise ValueError

        self._items[key] = value

        if value.id_key in self._playerset:
            value.player = self._playerset[value.id_key]

        value.before_updated.connect(self._at_user_updated)
        _transaction.emit(self.added, value)
        self.before_added.emit(value, _transaction)

    def __setitem__(self, key, value):
        # CAVEAT: use only as an entry point for model changes.
        self.set_item(key, value)

    @transactional
    def del_item(self, item, _transaction=None):
        try:
            user = self[item]
        except KeyError:
            return
        del self._items[user.id_key]
        user.before_updated.disconnect(self._at_user_updated)
        _transaction.emit(self.removed, user)
        self.before_removed.emit(item, _transaction)

    def __delitem__(self, item):
        # CAVEAT: use only as an entry point for model changes.
        self.del_item(item)

    @transactional
    def clear(self, _transaction=None):
        oldusers = list(self.keys())
        for user in oldusers:
            self.del_item(user, _transaction)

    def _at_player_added(self, player, _transaction=None):
        if player.login in self:
            self[player.login].set_player(player, _transaction)

    def _at_player_removed(self, player, _transaction=None):
        if player.login in self:
            self[player.login].set_player(None, _transaction)

    def _at_user_updated(self, user, olduser, _transaction=None):
        if user.name != olduser.name:
            self._handle_rename(user, olduser, _transaction)

    def _handle_rename(self, user, olduser, _transaction=None):
        # We should never rename to an existing user, but let's handle it
        if user.name in self:
            self.del_item(user.name, _transaction)

        if olduser.name in self._items:
            del self._items[olduser.name]
        self._items[user.name] = user

        newplayer = self._playerset.get(user.name)
        user.set_player(newplayer, _transaction)
