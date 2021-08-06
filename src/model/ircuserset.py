from model.ircuser import IrcUser
from model.modelitemset import ModelItemSet
from model.transaction import transactional


class IrcUserset(ModelItemSet):
    def __init__(self, playerset):
        ModelItemSet.__init__(self)
        self._playerset = playerset
        playerset.before_added.connect(self._at_player_added)
        playerset.before_removed.connect(self._at_player_removed)

    @transactional
    def set_item(self, key, value, _transaction=None):
        if not isinstance(key, str) or not isinstance(value, IrcUser):
            raise TypeError
        ModelItemSet.set_item(self, key, value, _transaction)
        if value.id_key in self._playerset:
            value.player = self._playerset[value.id_key]
        value.before_updated.connect(self._at_user_updated)
        self.emit_added(value, _transaction)

    @transactional
    def del_item(self, key, _transaction=None):
        user = ModelItemSet.del_item(self, key, _transaction)
        if user is None:
            return
        user.before_updated.disconnect(self._at_user_updated)
        self.emit_removed(user, _transaction)

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
