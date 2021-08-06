from PyQt5.QtCore import pyqtSignal

from model.modelitem import ModelItem
from model.transaction import transactional


class Chatter(ModelItem):
    newPlayer = pyqtSignal(object, object, object)
    added_channel = pyqtSignal(object)
    removed_channel = pyqtSignal(object)

    def __init__(self, name, hostname):
        ModelItem.__init__(self)
        self.add_field("name", name)
        self.add_field("hostname", hostname)
        self._player = None
        self.channels = {}

    @property
    def id_key(self):
        return self.name

    def copy(self):
        return Chatter(**self.field_dict)

    @transactional
    def update(self, **kwargs):
        _transaction = kwargs.pop("_transaction")
        olduser = self.copy()
        ModelItem.update(self, **kwargs)
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

    @transactional
    def add_channel(self, cc, _transaction=None):
        self.channels[cc.id_key] = cc
        _transaction.emit(self.added_channel, cc)

    @transactional
    def remove_channel(self, cc, _transaction=None):
        del self.channels[cc.id_key]
        _transaction.emit(self.removed_channel, cc)

    def is_base_channel_mod(self):
        return any(cc.is_mod() for cc in self.channels.values()
                   if cc.channel.is_base)
