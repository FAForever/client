from PyQt5.QtCore import pyqtSignal
from model.qobjectmapping import QObjectMapping


class IrcUserset(QObjectMapping):
    added = pyqtSignal(object)
    removed = pyqtSignal(object)

    def __init__(self, playerset):
        QObjectMapping.__init__(self)
        self._items = {}
        self._playerset = playerset
        playerset.added.connect(self._at_player_added)
        playerset.removed.connect(self._at_player_removed)

    def __getitem__(self, item):
        return self._items[item]

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __setitem__(self, key, value):
        if key in self:     # disallow overwriting existing chatters
            raise ValueError

        if key != value.id_key:
            raise ValueError

        self._items[key] = value

        if value.id_key in self._playerset:
            value.player = self._playerset[value.id_key]

        # We're first to connect, so first to get called
        value.updated.connect(self._at_user_updated)

        self.added.emit(value)

    def __delitem__(self, item):
        try:
            user = self[item]
        except KeyError:
            return
        del self._items[user.id_key]
        user.updated.disconnect(self._at_user_updated)
        self.removed.emit(user)

    def clear(self):
        oldusers = list(self.keys())
        for user in oldusers:
            del self[user]

    def _at_player_added(self, player):
        if player.login in self:
            self[player.login].player = player

    def _at_player_removed(self, player):
        if player.login in self:
            self[player.login].player = None

    def _at_user_updated(self, user, olduser):
        if user.name != olduser.name:
            self._handle_rename(user, olduser)

    def _handle_rename(self, user, olduser):
        # We should never rename to an existing user, but let's handle it
        if user.name in self:
            del self[user.name]

        if olduser.name in self._items:
            del self._items[olduser.name]
        self._items[user.name] = user

        newplayer = self._playerset.get(user.name)
        user.player = newplayer
