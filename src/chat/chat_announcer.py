from model.chat.channel import ChannelID, ChannelType
from model.chat.chatline import ChatLine, ChatLineType


class ChatAnnouncer:
    def __init__(self, model, chat_config, game_announcer,
                 line_metadata_builder):
        self._model = model
        self._chat_config = chat_config
        self._game_announcer = game_announcer
        self._line_metadata_builder = line_metadata_builder
        self._game_announcer.announce.connect(self._announce)

    @property
    def _announcement_channels(self):
        return self._chat_config.announcement_channels

    def _announce(self, msg, sender=None):
        line = ChatLine(sender, msg, ChatLineType.ANNOUNCEMENT)
        for name in self._announcement_channels:
            cid = ChannelID(ChannelType.PUBLIC, name)
            channel = self._model.channels.get(cid, None)
            if channel is None:
                continue
            data = self._line_metadata_builder.get_meta(channel, line)
            channel.lines.add_line(data)
