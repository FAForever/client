from model.modelitemset import ModelItemSet
from model.transaction import transactional


class Channelset(ModelItemSet):

    def __init__(self):
        ModelItemSet.__init__(self)

    @transactional
    def set_item(self, key, value, _transaction=None):
        ModelItemSet.set_item(self, key, value, _transaction)
        self.emit_added(value, _transaction)

    @transactional
    def del_item(self, key, _transaction=None):
        channel = ModelItemSet.del_item(self, key, _transaction)
        if channel is None:
            return
        self.emit_removed(channel, _transaction)
