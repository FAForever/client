from model.chat.channel import ChannelType
from model.chat.chatline import ChatLine, ChatLineType
from util import irc_escape

class ChatGreeter:
    def __init__(self, model, theme, chat_config, line_metadata_builder):
        self._model = model
        self._model.channels.added.connect(self._at_channel_added)
        self._chat_config = chat_config
        self._line_metadata_builder = line_metadata_builder
        self._greeted_channels = set()
        self._greeting_format = theme.readfile("chat/raw.qhtml")

    @property
    def _greeting(self):
        return self._chat_config.channel_greeting

    @property
    def _channels(self):
        return self._chat_config.channels_to_greet_in

    def _at_channel_added(self, channel):
        cid = channel.id_key
        if cid in self._greeted_channels:
            return
        if cid.type != ChannelType.PUBLIC or cid.name not in self._channels:
            return
        self._print_greeting(channel)
        self._greeted_channels.add(cid)

    def _print_greeting(self, channel):
        for line in self._greeting:
            text, color, size = line
            text = irc_escape(text)
            msg = self._greeting_format.format(text=text, color=color,
                                               size=size)
            line = ChatLine(None, msg, ChatLineType.RAW)
            data = self._line_metadata_builder.get_meta(channel, line)
            channel.lines.add_line(data)
