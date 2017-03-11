from PyQt5 import QtCore

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

class User(QtCore.QObject):
    """
    Represents the person using the FAF Client. May have a player assigned to
    himself if he's logged in, has foes, friends and clannies.
    """
    relationsUpdated = QtCore.pyqtSignal(set)

    def __init__(self):
        QtCore.QObject.__init__(self)

        self._player = None
        self._friends = UserRelation()
        self._foes = UserRelation()
        self._clannies = UserRelation()

        self._friends.updated.connect(self.relationsUpdated.emit)
        self._foes.updated.connect(self.relationsUpdated.emit)
        self._clannies.updated.connect(self.relationsUpdated.emit)

    @property
    def player(self):
        return self._player

    @player.setter
    def player(self, value):
        self._player = value

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
