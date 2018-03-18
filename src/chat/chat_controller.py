from model.chat.channel import Channel, Lines, ChannelID, ChannelType
from model.chat.chatter import Chatter
from model.chat.chatline import ChatLine, ChatLineType
from model.chat.channelchatter import ChannelChatter
from enum import Enum


class ChatController:
    def __init__(self, connection, model, user_relations, chat_config,
                 line_metadata_builder):
        self._connection = connection
        self._model = model
        self._user_relations = user_relations
        self._chat_config = chat_config
        self._chat_config.updated.connect(self._at_config_updated)
        self._line_metadata_builder = line_metadata_builder

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
    def build(cls, connection, model, user_relations, chat_config,
              line_metadata_builder, **kwargs):
        return cls(connection, model, user_relations, chat_config,
                   line_metadata_builder)

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
                self._add_me_to_channel(channel)
        return self._channels[cid]

    def _add_me_to_channel(self, channel):
        my_name = self._connection.nickname
        me = None if my_name is None else self._chatters.get(my_name, None)
        if me is not None:
            cc = ChannelChatter(channel, me, "")
            self._ccs[(channel.id_key, me.id_key)] = cc

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

    def _add_line(self, channel, line):
        data = self._line_metadata_builder.get_meta(channel, line)
        channel.lines.add_line(data)
        self._trim_channel_lines(channel)

    def _at_new_line(self, cid, cinfo, line):
        if (cid.type == ChannelType.PUBLIC and cid not in self._channels):
            return
        if self._should_ignore_chatter(cid, line.sender):
            return
        self._check_add_new_channel(cid)

        # If a chatter messages us without having joined any channel, this is
        # where we first hear of him
        if cinfo is not None and cinfo.name not in self._chatters:
            self._check_add_new_chatter(cinfo)
            self._add_or_update_cc(cid, cinfo)

        self._add_line(self._channels[cid], line)

    def _at_new_channel_chatters(self, cid, chatters):
        for c in chatters:
            self._add_or_update_cc(cid, c)

    def _at_channel_chatter_joined(self, cid, chatter):
        self._at_new_channel_chatters(cid, [chatter])
        self._announce_join(cid, chatter)

    def _at_channel_chatter_left(self, cid, chatter):
        self._announce_part(cid, chatter)
        self._remove_cc(cid, chatter)

    def _at_chatter_quit(self, chatter, msg):
        chatter_obj = self._chatters.get(chatter.name, None)
        if chatter_obj is None:
            return
        for cc in chatter_obj.channels.values():
            self._announce_quit(cc.channel.id_key, chatter, msg)
        self._chatters.pop(chatter.name, None)

    def _joinpart(fn):
        def wrap(self, cid, chatter, *args, **kwargs):
            if not self._chat_config.joinsparts:
                return
            if self._should_ignore_chatter(cid, chatter.name):
                return
            channel = self._channels.get(cid, None)
            if channel is None:
                return
            return fn(self, channel, chatter, *args, **kwargs)
        return wrap

    def _announce_chatter(self, channel, chatter, text):
        line = ChatLine(chatter.name, text, ChatLineType.INFO)
        self._add_line(channel, line)

    @_joinpart
    def _announce_join(self, channel, chatter):
        self._announce_chatter(channel, chatter, "joined the channel.")

    @_joinpart
    def _announce_part(self, channel, chatter):
        self._announce_chatter(channel, chatter, "left the channel.")

    @_joinpart
    def _announce_quit(self, channel, chatter, message):
        prefix = "quit"
        if message == chatter.name:     # Silence default messages
            message = "{}.".format(prefix)
        else:
            message = "{}: {}".format(prefix, message)
        self._announce_chatter(channel, chatter, message)

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
        self._channels.clear()
        self._chatters.clear()
        self._ccs.clear()
        self._model.connected = True

    def _at_disconnected(self):
        self._model.connected = False

    def _at_new_server_message(self, msg):
        self._model.add_server_message(msg)

    def _at_config_updated(self, option):
        if option == "max_chat_lines":
            for channel in self._channels.values:
                self._trim_channel_lines(channel)

    def _trim_channel_lines(self, channel):
        max_ = self._chat_config.max_chat_lines
        trim_count = self._chat_config.chat_line_trim_count
        if len(channel.lines) <= max_:
            return
        trim_amount = min(len(channel.lines), trim_count)
        channel.lines.remove_lines(trim_amount)

    # User actions start here.
    def send_message(self, cid, message):
        action, msg = MessageAction.parse_message(message)
        if action == MessageAction.MSG:
            if self._connection.send_message(cid.name, msg):
                self._at_new_line(cid, None, self._user_chat_line(msg))
        elif action == MessageAction.PRIVMSG:
            chatter_name, msg = msg.split(" ", 1)
            if self._connection.send_message(chatter_name, msg):
                cid = ChannelID.private_cid(chatter_name)
                self._at_new_line(cid, None, self._user_chat_line(msg))
        elif action == MessageAction.ME:
            if self._connection.send_action(cid.name, msg):
                self._at_new_line(cid, None, self._user_chat_line(
                    msg, ChatLineType.ACTION))
        elif action == MessageAction.SEEN:
            self._connection.send_action("nickserv", "info {}".format(msg))
        elif action == MessageAction.TOPIC:
            self._connection.set_topic(cid.name, msg)
        elif action == MessageAction.JOIN:
            self._connection.join(msg)
        else:
            pass    # TODO - raise 'Sending failed' error back to the view?

    def join_channel(self, cid):
        # Don't join a private channel with ourselves
        if (cid.type == ChannelType.PRIVATE and
                cid.name == self._connection.nickname):
            return

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

    def _should_ignore_chatter(self, cid, name):
        if name is None:
            return False
        cc = self._ccs.get((cid, name), None)
        if cc is None:
            return False
        if cc.is_mod():
            return False
        name = cc.chatter.name
        id_ = None if cc.chatter.player is None else cc.chatter.player.id
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
