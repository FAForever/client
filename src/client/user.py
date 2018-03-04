from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal
from collections.abc import MutableSet
from config import Settings


class SetSignals(QObject):
    """
    Defined separately since QObject and MutableSet metaclasses clash.
    """
    added = pyqtSignal(object)
    removed = pyqtSignal(object)

    def __init__(self):
        QObject.__init__(self)


class SignallingSet(MutableSet):
    def __init__(self):
        MutableSet.__init__(self)
        self._set = set()
        self._signals = SetSignals()

    @property
    def added(self):
        return self._signals.added

    @property
    def removed(self):
        return self._signals.removed

    def __contains__(self, value):
        return value in self._set

    def __iter__(self):
        return iter(self._set)

    def __len__(self):
        return len(self._set)

    def add(self, value):
        if value not in self._set:
            self._set.add(value)
            self.added.emit(value)

    def discard(self, value):
        if value in self._set:
            self._set.discard(value)
            self.removed.emit(value)


class SavingSignallingSet(SignallingSet):
    def __init__(self, key, settings):
        SignallingSet.__init__(self)
        self._settings = settings
        self.key = key

    def _loadRelations(self):
        self.clear()
        if self._key is None:
            return
        rel = self._settings.get(self._key)
        if rel is not None:
            self |= set(rel)

    def _saveRelations(self):
        if self._key is None:
            return
        self._settings.set(self._key, list(self))

    def add(self, value):
        SignallingSet.add(self, value)
        self._saveRelations()

    def discard(self, value):
        SignallingSet.discard(self, value)
        self._saveRelations()

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, value):
        self._key = value
        self._loadRelations()


class User(QtCore.QObject):
    """
    Represents the person using the FAF Client. May have a player assigned to
    himself if he's logged in, has foes, friends and clannies.
    """
    relationsUpdated = QtCore.pyqtSignal(set)
    ircRelationsUpdated = QtCore.pyqtSignal(set)
    playerChanged = QtCore.pyqtSignal(object)

    def __init__(self, playerset):
        QtCore.QObject.__init__(self)

        self._player = None
        self.id = None
        self.login = None

        self._players = playerset
        self._players.added.connect(self._on_player_change)
        self._players.removed.connect(self._on_player_change)

        self._friends = SignallingSet()
        self._foes = SignallingSet()
        self._friends.added.connect(self._updated)
        self._friends.removed.connect(self._updated)
        self._foes.added.connect(self._updated)
        self._foes.removed.connect(self._updated)

        self._irc_friends = SavingSignallingSet(None, Settings)
        self._irc_foes = SavingSignallingSet(None, Settings)
        self._irc_friends.added.connect(self._irc_updated)
        self._irc_friends.removed.connect(self._irc_updated)
        self._irc_foes.added.connect(self._irc_updated)
        self._irc_foes.removed.connect(self._irc_updated)

    def _updated(self, value):
        self.relationsUpdated.emit(set(value))

    def _irc_updated(self, value):
        self.ircRelationsUpdated.emit(set(value))

    @property
    def player(self):
        return self._player

    def onLogin(self, login, id_):
        self.login = login
        self.id = id_
        self._update_player()

    def _update_player(self):
        if self.id not in self._players:
            self._player = None
        elif self._player is not None:
            return
        else:
            self._player = self._players[self.id]
        self._irc_friends.key = self._irc_key("friends")
        self._irc_foes.key = self._irc_key("foes")
        self.playerChanged.emit(self._player)

    def _on_player_change(self, player):
        if self.id is None or player.id != self.id:
            return
        self._update_player()

    def _irc_key(self, name):
        if self.player is None:
            return None
        return "chat.irc_" + name + "/" + str(self.player.id)

    def resetPlayer(self):
        self._player = None
        self._friends.clear()
        self._foes.clear()
        self._clannies.clear()

    def isClannie(self, _id):
        if not self._player:
            return False
        return self._isClannie(_id, self._player.clan)

    def _isClannie(self, _id, my_clan):
        if my_clan is None:
            return False
        other = self._players.get(_id)
        if other is None:
            return False
        return my_clan == other.clan

    def _getClannies(self, clan):
        return [p.id for p in self._players.values() if self._isClannie(p.id, clan)]

    def _checkClanChange(self, new, old):
        if new.clan == old.clan:
            return
        oldClannies = self._getClannies(old.clan)
        newClannies = self._getClannies(new.clan)
        self.relationsUpdated.emit(set(oldClannies + newClannies))

    def addFriend(self, id_):
        self._friends.add(id_)

    def remFriend(self, id_):
        self._friends.discard(id_)

    def setFriends(self, ids):
        self._friends.clear()
        self._friends |= set(ids)

    def addFoe(self, id_):
        self._foes.add(id_)

    def remFoe(self, id_):
        self._foes.discard(id_)

    def setFoes(self, ids):
        self._foes.clear()
        self._foes |= set(ids)

    def addIrcFriend(self, id_):
        self._irc_friends.add(id_)

    def remIrcFriend(self, id_):
        self._irc_friends.discard(id_)

    def setIrcFriends(self, ids):
        self._irc_friends.clear()
        self._irc_friends |= set(ids)

    def addIrcFoe(self, id_):
        self._irc_foes.add(id_)

    def remIrcFoe(self, id_):
        self._irc_foes.discard(id_)

    def setIrcFoes(self, ids):
        self._irc_foes.clear()
        self._irc_foes |= set(ids)

    def isFriend(self, id_=-1, name=None):
        if id_ != -1:
            return id_ in self._friends
        elif name is not None:
            return name in self._irc_friends
        return False

    def isFoe(self, id_=-1, name=None):
        if id_ != -1:
            return id_ in self._foes
        elif name is not None:
            return name in self._irc_foes
        return False
