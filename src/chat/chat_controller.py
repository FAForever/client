from model.chat.channel import Channel, Lines
from model.chat.chatter import Chatter
from model.chat.channelchatter import ChannelChatter


class ChatController:
    def __init__(self, connection, model):
        self._connection = connection
        self._model = model

        c = connection
        c.new_line.connect(self._at_new_line)
        c.new_channel_chatters.connect(self._at_new_channel_chatters)
        c.channel_chatters_left.connect(self._at_channel_chatters_left)
        c.chatters_quit.connect(self._at_chatters_quit)
        c.quit_channel.connect(self._at_quit_channel)
        c.chatter_renamed.connect(self._at_chatter_renamed)
        c.new_chatter_elevation.connect(self._at_new_chatter_elevation)
        c.new_channel_topic.connect(self._at_new_channel_topic)
        c.disconnected.connect(self._at_disconnected)

    @property
    def _channels(self):
        return self._model.channels

    @property
    def _chatters(self):
        return self._model.chatters

    @property
    def _ccs(self):
        return self._model.channelchatters

    def _check_add_new_channel(self, cid):
        if cid not in self._channels:
            channel = Channel(cid, Lines(), "")
            self._channels[cid] = channel
        return self._channels[cid]

    def _check_add_new_chatter(self, cinfo):
        if cinfo.name not in self._chatters:
            chatter = Chatter(cinfo.name, cinfo.hostname)
            self._chatters[chatter.name] = chatter
        return self._chatters[cinfo.name]

    def _add_or_update_cc(self, cid, cinfo):
        channel = self._check_add_new_channel(cid)
        chatter = self._check_add_new_chatter(cinfo)
        key = (channel.id_key, chatter.id_key)
        if key not in self._ccs:
            cc = ChannelChatter(channel, chatter, cinfo.elevation)
            self._ccs[key] = cc
        else:
            self._ccs[key].update(elevation=cinfo.elevation)

    def _remove_cc(self, cid, cinfo):
        key = (cid, cinfo.name)
        del self._ccs[key]

    def _at_new_line(self, line, cid):
        if cid not in self._channels:
            return
        self._channels[cid].lines.add_line(line)

    def _at_new_channel_chatters(self, cid, chatters):
        for c in chatters:
            self._add_or_update_cc(cid, c)

    def _at_channel_chatters_left(self, cid, chatters):
        for c in chatters:
            self._remove_cc(cid, c)

    def _at_chatters_quit(self, chatters):
        for c in chatters:
            del self._chatters[c.name]

    def _at_quit_channel(self, cid):
        del self._channels[cid]

    def _at_chatter_renamed(self, old, new):
        if old not in self._chatters:
            return
        self._chatters[old].update(name=new)

    def _at_new_chatter_elevation(self, cid, chatter, added, removed):
        key = (cid, chatter.name)
        if key not in self._ccs:
            return
        cc = self._ccs[key]
        old = cc.elevation
        new = ''.join(c for c in old + added if c not in removed)
        cc.update(elevation=new)

    def _at_new_channel_topic(self, cid, topic):
        channel = self._channels.get(cid)
        if channel is None:
            return
        channel.update(topic=topic)

    def _at_disconnected(self):
        self._channels.clear()
        self._chatters.clear()
        self._ccs.clear()
