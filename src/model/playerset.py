from model.modelitemset import ModelItemSet
from model.player import Player
from model.transaction import transactional


class Playerset(ModelItemSet):
    def __init__(self):
        ModelItemSet.__init__(self)
        # Login -> Player map
        self._logins = {}

    def __getitem__(self, item):
        if isinstance(item, int):
            return ModelItemSet.__getitem__(self, item)
        if isinstance(item, str):
            return self._logins[item]
        raise TypeError

    def getID(self, name):
        if name in self:
            return self[name].id
        return -1

    @transactional
    def set_item(self, key, value, _transaction=None):
        if not isinstance(key, int) or not isinstance(value, Player):
            raise TypeError

        ModelItemSet.set_item(self, key, value, _transaction)
        self._logins[value.login] = value
        self.emit_added(value, _transaction)

    @transactional
    def del_item(self, key, _transaction=None):
        player = ModelItemSet.del_item(self, key, _transaction)
        if player is None:
            return
        del self._logins[player.login]
        self.emit_removed(player, _transaction)

    def __delitem__(self, item):
        # CAVEAT: use only as an entry point for model changes.
        self.del_item(item)
