from PyQt5 import QtCore
from config import Settings
from enum import Enum


class UserRelation(QtCore.QObject):
    """
    Represents some sort of relation user has with other players.
    """
    updated = QtCore.pyqtSignal(set)

    def __init__(self):
        QtCore.QObject.__init__(self)
        self._relations = set()

    def add(self, value):
        self._relations.add(value)
        self.updated.emit(set([value]))

    def rem(self, value):
        self._relations.discard(value)
        self.updated.emit(set([value]))

    def set(self, values):
        changed = self._relations.union(set(values))
        self._relations = set(values)
        self.updated.emit(changed)

    def clear(self):
        self.set(set())

    def has(self, value):
        return value in self._relations


class IrcUserRelation(UserRelation):
    """
    Represents a relation user has with IRC users. Remembers the relation
    in the Settings.
    """

    def __init__(self, key=None):
        UserRelation.__init__(self)
        self.key = key

    def _loadRelations(self):
        if self._key is not None:
            rel = Settings.get(self._key)
            self._relations = set(rel) if rel is not None else set()
        else:
            self._relations = set()

    def _saveRelations(self):
        if self._key is not None:
            Settings.set(self._key, list(self._relations))

    def add(self, value):
        UserRelation.add(self, value)
        self._saveRelations()

    def rem(self, value):
        UserRelation.rem(self, value)
        self._saveRelations()

    def set(self, values):
        UserRelation.set(self, values)
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
    playerAvailable = QtCore.pyqtSignal()

    def __init__(self, playerset):
        QtCore.QObject.__init__(self)

        self._player = None
        self.id = None
        self.login = None

        self._players = playerset
        self._players.added.connect(self._on_player_change)
        self._players.removed.connect(self._on_player_change)

        self._friends = UserRelation()
        self._foes = UserRelation()
        self._friends.updated.connect(self._relations_updated)
        self._foes.updated.connect(self._relations_updated)

        self._irc_friends = IrcUserRelation()
        self._irc_foes = IrcUserRelation()
        self._irc_friends.updated.connect(self._irc_relations_updated)
        self._irc_foes.updated.connect(self._irc_relations_updated)

    def _relations_updated(self, items):
        self.relationsUpdated.emit(items)

    def _irc_relations_updated(self, items):
        self.ircRelationsUpdated.emit(items)

    @property
    def player(self):
        return self._player

    def onLogin(self, login, id_):
        self.login = login
        self.id = id_
        self._update_player()

    def _update_player(self):
        if self.id is None or self.id not in self._players:
            self._player = None
            return
        if self._player is not None:
            return
        self._player = self._players[self.id]
        self.playerAvailable.emit()

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
        self._friends.rem(id_)

    def setFriends(self, ids):
        self._friends.set(ids)

    def addFoe(self, id_):
        self._foes.add(id_)

    def remFoe(self, id_):
        self._foes.rem(id_)

    def setFoes(self, ids):
        self._foes.set(ids)

    def addIrcFriend(self, id_):
        self._irc_friends.add(id_)

    def remIrcFriend(self, id_):
        self._irc_friends.rem(id_)

    def setIrcFriends(self, ids):
        self._irc_friends.set(ids)

    def addIrcFoe(self, id_):
        self._irc_foes.add(id_)

    def remIrcFoe(self, id_):
        self._irc_foes.rem(id_)

    def setIrcFoes(self, ids):
        self._irc_foes.set(ids)

    def isFriend(self, id_=-1, name=None):
        if id_ != -1:
            return self._friends.has(id_)
        elif name is not None:
            return self._irc_friends.has(name)
        return False

    def isFoe(self, id_=-1, name=None):
        if id_ != -1:
            return self._foes.has(id_)
        elif name is not None:
            return self._irc_foes.has(name)
        return False
