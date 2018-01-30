from PyQt5.QtCore import pyqtSignal

from model.qobjectmapping import QObjectMapping
from model.player import Player
from model.transaction import transactional


class Playerset(QObjectMapping):
    """
    Wrapper for an id->Player map

    Used to lookup players either by id or by login.
    """
    added = pyqtSignal(object)
    removed = pyqtSignal(object)
    before_added = pyqtSignal(object, object)
    before_removed = pyqtSignal(object, object)

    def __init__(self):
        QObjectMapping.__init__(self)

        # UID -> Player map
        self._items = {}
        # Login -> Player map
        self._logins = {}

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._items[item]
        if isinstance(item, str):
            return self._logins[item]
        raise TypeError

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def getID(self, name):
        if name in self:
            return self[name].id
        return -1

    @transactional
    def set_item(self, key, value, _transaction=None):
        if not isinstance(key, int) or not isinstance(value, Player):
            raise TypeError

        if key in self:     # disallow overwriting existing players
            raise ValueError

        if key != value.id_key:
            raise ValueError

        self._items[key] = value
        self._logins[value.login] = value
        _transaction.emit(self.added, value)
        self.before_added.emit(value, _transaction)

    def __setitem__(self, key, value):
        # CAVEAT: use only as an entry point for model changes.
        self.set_item(key, value)

    @transactional
    def del_item(self, item, _transaction=None):
        try:
            player = self[item]
        except KeyError:
            return
        del self._items[player.id_key]
        del self._logins[player.login]
        _transaction.emit(self.removed, player)
        self.before_removed.emit(player, _transaction)

    def __delitem__(self, item):
        # CAVEAT: use only as an entry point for model changes.
        self.del_item(item)

    @transactional
    def clear(self, _transaction=None):
        oldplayers = list(self.keys())
        for player in oldplayers:
            self.del_item(player, _transaction)
