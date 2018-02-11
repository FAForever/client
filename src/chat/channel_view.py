from chat.channel_widget import ChannelWidget
from chat.chatter_model import ChatterModel, ChatterItemDelegate


class ChannelView:
    def __init__(self, channel):
        self._channel = channel
        self.widget = ChannelWidget()
        self.widget.set_chatter_delegate(ChatterItemDelegate())
        self.widget.set_chatter_model(ChatterModel(channel))
        channel.lines.added.connect(self._add_line)

    def _add_line(self, number):
        for line in self._channel.lines[-number:]:
            self.widget.append_line(line)
