from PyQt5.QtCore import QObject, pyqtSignal


class IrcUser(QObject):
    updated = pyqtSignal(object, object)
    newPlayer = pyqtSignal(object, object, object)

    def __init__(self, name, hostname):
        QObject.__init__(self)

        self.name = name

        self.elevation = {}
        self.hostname = hostname

        self._player = None

    def copy(self):
        old = IrcUser(self.name, self.hostname)
        for channel in self.elevation:
            old.set_elevation(channel, self.elevation[channel])
        return old

    def update(self, name=None, hostname=None):
        olduser = self.copy()

        if name is not None:
            self.name = name
        if hostname is not None:
            self.hostname = hostname

        self.updated.emit(self, olduser)

    def set_elevation(self, channel, elevation):
        olduser = self.copy()
        if elevation is None:
            if channel in self.elevation:
                del self.elevation[channel]
        else:
            self.elevation[channel] = elevation
        self.updated.emit(self, olduser)

    @property
    def player(self):
        return self._player

    @player.setter
    def player(self, val):
        oldplayer = self._player
        self._player = val
        self.newPlayer.emit(self, val, oldplayer)

    def is_mod(self, channel):
        if channel not in self.elevation:
            return False
        return self.elevation[channel] in "~&@%+"
