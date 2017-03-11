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

    def __init__(self, key = None):
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


class PlayerAffiliation(Enum):
    SELF = "self"
    FRIEND = "friend"
    FOE = "foe"
    CLANNIE = "clan"
    OTHER = "default"

class User(QtCore.QObject):
    """
    Represents the person using the FAF Client. May have a player assigned to
    himself if he's logged in, has foes, friends and clannies.
    """
    relationsUpdated = QtCore.pyqtSignal(set)
    ircRelationsUpdated = QtCore.pyqtSignal(set)

    def __init__(self):
        QtCore.QObject.__init__(self)

        self._player = None
        self._friends = UserRelation()
        self._foes = UserRelation()
        self._clannies = UserRelation()

        self._friends.updated.connect(self.relationsUpdated.emit)
        self._foes.updated.connect(self.relationsUpdated.emit)
        self._clannies.updated.connect(self.relationsUpdated.emit)

        self._irc_friends = IrcUserRelation()
        self._irc_foes = IrcUserRelation()

        self._irc_friends.updated.connect(self.ircRelationsUpdated.emit)
        self._irc_foes.updated.connect(self.ircRelationsUpdated.emit)

    @property
    def player(self):
        return self._player

    @player.setter
    def player(self, value):
        self._player = value
        # reload IRC friends from settings
        self._irc_friends.key = self._irc_key("friends")
        self._irc_foes.key = self._irc_key("foes")

    def _irc_key(self, name):
        if self.player is None:
            return None
        return "chat.irc_" + name + "/" + str(self.player.id)

    def resetPlayer():
        self._player = None
        self._friends.clear()
        self._foes.clear()
        self._clannies.clear()

    def addFriend(self, id_):
        self._friends.add(id_)
    def remFriend(self, id_):
        self._friends.rem(id_)
    def setFriends(self, ids):
        self._friends.set(ids)
    def isFriend(self, id_):
        return self._friends.has(id_)

    def addFoe(self, id_):
        self._foes.add(id_)
    def remFoe(self, id_):
        self._foes.rem(id_)
    def setFoes(self, ids):
        self._foes.set(ids)
    def isFoe(self, id_):
        return self._foes.has(id_)

    def addClannie(self, id_):
        self._clannies.add(id_)
    def setClannies(self, ids):
        self._clannies.set(ids)
    def isClannie(self, id_):
        return self._clannies.has(id_)

    def addIrcFriend(self, id_):
        self._irc_friends.add(id_)
    def remIrcFriend(self, id_):
        self._irc_friends.rem(id_)
    def setIrcFriends(self, ids):
        self._irc_friends.set(ids)
    def isIrcFriend(self, id_):
        return self._irc_friends.has(id_)

    def addIrcFoe(self, id_):
        self._irc_foes.add(id_)
    def remIrcFoe(self, id_):
        self._irc_foes.rem(id_)
    def setIrcFoes(self, ids):
        self._irc_foes.set(ids)
    def isIrcFoe(self, id_):
        return self._irc_foes.has(id_)

    def getAffiliation(self, id_):
        if self.player and self.player.id == id_:
            return PlayerAffiliation.SELF
        if self.isFriend(id_):
            return PlayerAffiliation.FRIEND
        if self.isFoe(id_):
            return PlayerAffiliation.FOE
        if self.isClannie(id_):
            return PlayerAffiliation.CLANNIE
        return PlayerAffiliation.OTHER

    def getIrcAffiliation(self, name):
        if self.isIrcFriend(name):
            return PlayerAffiliation.FRIEND
        if self.isIrcFoe(name):
            return PlayerAffiliation.FOE
        return PlayerAffiliation.OTHER
