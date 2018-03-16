from model.chat.channel import Channel, Lines, ChannelID, ChannelType
from model.chat.chatter import Chatter
from model.chat.chatline import ChatLine, ChatLineType
from model.chat.channelchatter import ChannelChatter
from enum import Enum


class ChatController:
    def __init__(self, connection, model, user_relations):
        self._connection = connection
        self._model = model
        self._user_relations = user_relations

        c = connection
        c.new_line.connect(self._at_new_line)
        c.new_channel_chatters.connect(self._at_new_channel_chatters)
        c.channel_chatter_left.connect(self._at_channel_chatter_left)
        c.channel_chatter_joined.connect(self._at_channel_chatter_joined)
        c.chatter_quit.connect(self._at_chatter_quit)
        c.quit_channel.connect(self._at_quit_channel)
        c.chatter_renamed.connect(self._at_chatter_renamed)
        c.new_chatter_elevation.connect(self._at_new_chatter_elevation)
        c.new_channel_topic.connect(self._at_new_channel_topic)
        c.connected.connect(self._at_connected)
        c.disconnected.connect(self._at_disconnected)
        c.new_server_message.connect(self._at_new_server_message)

    @classmethod
    def build(cls, connection, model, user_relations, **kwargs):
        return cls(connection, model, user_relations)

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
            if cid.type == ChannelType.PRIVATE:
                self._add_private_chatters(channel)
        return self._channels[cid]

    def _add_private_chatters(self, channel):
        my_name = self._connection.nickname
        other_name = channel.id_key.name
        me = None if my_name is None else self._chatters.get(my_name, None)
        other = self._chatters.get(other_name)
        for chatter in [me, other]:
            if chatter is None:
                continue
            cc = ChannelChatter(channel, chatter, "")
            self._ccs[(channel.id_key, chatter.id_key)] = cc

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
        self._ccs.pop(key, None)

    def _at_new_line(self, line, cid):
        # Private notices printed in public channels are our own invention.
        # Such a notice NEVER indicates joining a channel.
        if (line.type == ChatLineType.NOTICE and
                cid.type == ChannelType.PUBLIC and
                cid not in self._channels):
            return
        if self._should_ignore_chatter(line.sender):
            return
        self._check_add_new_channel(cid)
        self._channels[cid].lines.add_line(line)

    def _at_new_channel_chatters(self, cid, chatters):
        for c in chatters:
            self._add_or_update_cc(cid, c)

    def _at_channel_chatter_joined(self, cid, chatter):
        self._at_new_channel_chatters(cid, [chatter])

    def _at_channel_chatter_left(self, cid, chatter):
        self._remove_cc(cid, chatter)

    def _at_chatter_quit(self, chatter):
        self._chatters.pop(chatter, None)

    def _at_quit_channel(self, cid):
        self._delete_channel_ignoring_connection(cid)

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

    def _at_connected(self):
        self._model.connected = True

    def _at_disconnected(self):
        self._model.connected = False
        self._channels.clear()
        self._chatters.clear()
        self._ccs.clear()

    def _at_new_server_message(self, msg):
        self._model.add_server_message(msg)

    # User actions start here.
    def send_message(self, cid, message):
        action, msg = MessageAction.parse_message(message)
        if action == MessageAction.MSG:
            if self._connection.send_message(cid.name, msg):
                self._at_new_line(self._user_chat_line(msg), cid)
        elif action == MessageAction.PRIVMSG:
            chatter_name, msg = msg.split(" ", 1)
            if self._connection.send_message(chatter_name, msg):
                cid = ChannelID.private_cid(chatter_name)
                self._at_new_line(self._user_chat_line(msg), cid)
        elif action == MessageAction.ME:
            if self._connection.send_action(cid.name, msg):
                self._at_new_line(self._user_chat_line(msg,
                                                       ChatLineType.ACTION),
                                  cid)
        elif action == MessageAction.SEEN:
            self._connection.send_action("nickserv", "info {}".format(msg))
        elif action == MessageAction.TOPIC:
            self._connection.set_topic(cid.name, msg)
        elif action == MessageAction.JOIN:
            self._connection.join(msg)
        else:
            pass    # TODO - raise 'Sending failed' error back to the view?

    def join_channel(self, cid):
        if cid.type == ChannelType.PUBLIC:
            self._connection.join(cid.name)
        else:
            self._check_add_new_channel(cid)

    def join_public_channel(self, name):
        self.join_channel(ChannelID(ChannelType.PUBLIC, name))

    def _user_chat_line(self, msg, type_=ChatLineType.MESSAGE):
        return ChatLine(self._connection.nickname, msg, type_)

    def leave_channel(self, cid, reason):
        if cid.type == ChannelType.PRIVATE:
            self._delete_channel_ignoring_connection(cid)
        else:
            if not self._connection.part(cid.name, reason):
                # We're disconnected from IRC - allow user to close tabs anyway
                self._delete_channel_ignoring_connection(cid)

    def _delete_channel_ignoring_connection(self, cid):
        self._channels.pop(cid, None)

    def _should_ignore_chatter(self, name):
        chatter = self._chatters.get(name, None)
        if chatter is None:
            return False
        name = chatter.name
        id_ = None if chatter.player is None else chatter.player.id
        return self._user_relations.is_foe(id_, name)


class MessageAction(Enum):
    MSG = "message"
    UNKNOWN = "unknown"
    PRIVMSG = "/msg "
    ME = "/me "
    SEEN = "/seen "
    TOPIC = "/topic "
    JOIN = "/join "

    @classmethod
    def parse_message(cls, msg):
        if not msg.startswith("/"):
            return cls.MSG, msg

        for cmd in cls:
            if cmd in [cls.MSG, cls.UNKNOWN]:
                continue
            if msg.startswith(cmd.value):
                return cmd, msg[len(cmd.value):]

        return cls.UNKNOWN, msg
