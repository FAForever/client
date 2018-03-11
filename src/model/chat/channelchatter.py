from model.modelitem import ModelItem
from model.transaction import transactional


class ChannelChatter(ModelItem):
    MOD_ELEVATIONS = "~&@%+"

    def __init__(self, channel, chatter, elevation):
        ModelItem.__init__(self)
        self.channel = channel
        self.chatter = chatter
        self.add_field("elevation", elevation)

    @property
    def id_key(self):
        return (self.channel.id_key, self.chatter.id_key)

    def copy(self):
        return ChannelChatter(self.channel, self.chatter, **self.field_dict)

    @transactional
    def update(self, **kwargs):
        _transaction = kwargs.pop("_transaction")
        old = self.copy()
        ModelItem.update(self, **kwargs)
        self.emit_update(old, _transaction)

    @transactional
    def set_elevation(self, value, _transaction=None):
        self.update(elevation=value, _transaction=_transaction)

    def is_mod(self):
        e = self.elevation
        return e and e in self.MOD_ELEVATIONS
