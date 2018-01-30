from PyQt5.QtCore import QObject, pyqtSignal
from model.transaction import transactional


class IrcUser(QObject):
    before_updated = pyqtSignal(object, object, object)
    updated = pyqtSignal(object, object)
    newPlayer = pyqtSignal(object, object, object)

    def __init__(self, name, hostname):
        QObject.__init__(self)

        self.name = name

        self.elevation = {}
        self.hostname = hostname

        self._player = None

    @property
    def id_key(self):
        return self.name

    def __hash__(self):
        return hash(self.id_key)

    def copy(self):
        old = IrcUser(self.name, self.hostname)
        for channel in self.elevation:
            old.set_elevation(channel, self.elevation[channel])
        return old

    @transactional
    def update(self, name=None, hostname=None, _transaction=None):
        olduser = self.copy()

        if name is not None:
            self.name = name
        if hostname is not None:
            self.hostname = hostname

        _transaction.emit(self.updated, self, olduser)
        self.before_updated.emit(self, olduser, _transaction)

    @transactional
    def set_elevation(self, channel, elevation, _transaction=None):
        olduser = self.copy()
        if elevation is None:
            if channel in self.elevation:
                del self.elevation[channel]
        else:
            self.elevation[channel] = elevation
        _transaction.emit(self.updated, self, olduser)
        self.before_updated.emit(self, olduser, _transaction)

    @property
    def player(self):
        return self._player

    @transactional
    def set_player(self, val, _transaction=None):
        oldplayer = self._player
        self._player = val
        _transaction.emit(self.newPlayer, self, val, oldplayer)

    @player.setter
    def player(self, val):
        # CAVEAT: this will emit signals immediately!
        self.set_player(val)

    def is_mod(self, channel):
        if channel not in self.elevation:
            return False
        return self.elevation[channel] in "~&@%+"
