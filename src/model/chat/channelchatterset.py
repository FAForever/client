from model.modelitemset import ModelItemSet
from model.transaction import transactional


class ChannelChatterset(ModelItemSet):
    def __init__(self):
        ModelItemSet.__init__(self)

    @transactional
    def set_item(self, key, cc, _transaction=None):
        ModelItemSet.set_item(self, key, cc, _transaction)
        self.emit_added(cc, _transaction)

    @transactional
    def del_item(self, key, _transaction=None):
        chatter = ModelItemSet.del_item(self, key, _transaction)
        if chatter is None:
            return
        self.emit_removed(chatter, _transaction)


class ChatterChannelIndex:
    def __init__(self):
        self._by_channel = {}
        self._by_chatter = {}

    def ccs_by_chatter(self, chatter):
        return self._by_chatter.setdefault(chatter.id_key, set())

    def ccs_by_channel(self, channel):
        return self._by_channel.setdefault(channel.id_key, set())

    def add_cc(self, cc):
        self.ccs_by_chatter(cc.chatter).add(cc)
        self.ccs_by_channel(cc.channel).add(cc)

    def remove_cc(self, cc):
        chat_ccs = self.ccs_by_chatter(cc.chatter)
        chat_ccs.remove(cc)
        if not chat_ccs:
            del self._by_chatter[cc.chatter.id_key]

        chan_ccs = self.ccs_by_channel(cc.channel)
        chan_ccs.remove(cc)
        if not chan_ccs:
            del self._by_channel[cc.channel.id_key]


class ChannelChatterRelation:
    def __init__(self, channels, chatters, channelchatters):
        self._channels = channels
        self._chatters = chatters
        self._channelchatters = channelchatters
        self._index = ChatterChannelIndex()

        self._channelchatters.before_added.connect(self._new_cc)
        self._channelchatters.before_removed.connect(self._removed_cc)
        self._chatters.before_removed.connect(self._removed_chatter)
        self._channels.before_removed.connect(self._removed_channel)

    def _new_cc(self, cc, _transaction=None):
        self._index.add_cc(cc)
        cc.channel.add_chatter(cc, _transaction)
        cc.chatter.add_channel(cc, _transaction)

    def _removed_cc(self, cc, _transaction=None):
        self._index.remove_cc(cc)
        cc.channel.remove_chatter(cc, _transaction)
        cc.chatter.remove_channel(cc, _transaction)

    def _removed_chatter(self, chatter, _transaction):
        ccs = set(self._index.ccs_by_chatter(chatter))
        for cc in ccs:
            self._channelchatters.del_item(cc, _transaction)

    def _removed_channel(self, channel, _transaction):
        ccs = set(self._index.ccs_by_channel(channel))
        for cc in ccs:
            self._channelchatters.del_item(cc.id_key, _transaction)
