from PyQt5.QtCore import pyqtSignal
from model.transaction import transactional
from model.modelitem import ModelItem


class IrcUser(ModelItem):
    newPlayer = pyqtSignal(object, object, object)

    def __init__(self, name, hostname):
        ModelItem.__init__(self)

        self.elevation = {}
        self.add_field("name", name)
        self.add_field("hostname", hostname)

        self._player = None

    @property
    def id_key(self):
        return self.name

    def copy(self):
        old = IrcUser(**self.field_dict)
        for channel in self.elevation:
            old.set_elevation(channel, self.elevation[channel])
        return old

    @transactional
    def update(self, **kwargs):
        _transaction = kwargs.pop("_transaction")
        olduser = self.copy()
        ModelItem.update(self, **kwargs)
        self.emit_update(olduser, _transaction)

    @transactional
    def set_elevation(self, channel, elevation, _transaction=None):
        olduser = self.copy()
        if elevation is None:
            if channel in self.elevation:
                del self.elevation[channel]
        else:
            self.elevation[channel] = elevation
        self.emit_update(olduser, _transaction)

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
