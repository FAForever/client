from model.modelitemset import ModelItemSet
from model.transaction import transactional
from model.chat.channel import ChannelType

class Channelset(ModelItemSet):

    def __init__(self, base_channels):
        ModelItemSet.__init__(self)
        self.base_channels = base_channels

    @classmethod
    def build(cls, base_channels, **kwargs):
        return cls(base_channels)

    @transactional
    def set_item(self, key, value, _transaction=None):
        value.is_base = (key.type == ChannelType.PUBLIC
                         and key.name in self.base_channels)
        ModelItemSet.set_item(self, key, value, _transaction)
        self.emit_added(value, _transaction)

    @transactional
    def del_item(self, key, _transaction=None):
        channel = ModelItemSet.del_item(self, key, _transaction)
        if channel is None:
            return
        self.emit_removed(channel, _transaction)
