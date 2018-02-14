from chat.channel_widget import ChannelWidget
from chat.chatter_model import ChatterModel, ChatterItemDelegate


class ChannelView:
    def __init__(self, channel, controller):
        self._channel = channel
        self._controller = controller
        self.widget = ChannelWidget()
        self.widget.set_chatter_delegate(ChatterItemDelegate())
        self.widget.set_chatter_model(ChatterModel(channel))
        self.widget.line_typed.connect(self._at_line_typed)
        self.widget.set_autocompletion_source(self._channel)
        channel.lines.added.connect(self._add_line)

    def _add_line(self, number):
        for line in self._channel.lines[-number:]:
            self.widget.append_line(line)

    def _at_line_typed(self, line):
        self._controller.send_message(self._channel.id_key, line)
