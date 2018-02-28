from PyQt5.QtCore import QSize
from chat.channel_widget import ChannelWidget
from chat.chatter_model import ChatterModel, build_delegate


class ChannelView:
    def __init__(self, channel, controller, map_preview_dler, avatar_dler):
        self._channel = channel
        self._controller = controller
        self._map_preview_dler = map_preview_dler
        self._avatar_dler = avatar_dler

        self.widget = ChannelWidget(channel.id_key)
        self._delegate = build_delegate(QSize(150, 30), self.widget)
        self.widget.set_chatter_delegate(self._delegate)
        self.widget.set_chatter_tooltips(self._delegate.tooltip)

        model = ChatterModel(channel, map_preview_dler, avatar_dler)
        self.widget.set_chatter_model(model)

        self.widget.line_typed.connect(self._at_line_typed)
        self.widget.set_autocompletion_source(self._channel)
        self.widget.chatter_list_resized.connect(self._update_chatter_width)
        channel.lines.added.connect(self._add_line)

    def _add_line(self, number):
        for line in self._channel.lines[-number:]:
            self.widget.append_line(line)

    def _at_line_typed(self, line):
        self._controller.send_message(self._channel.id_key, line)

    def _update_chatter_width(self, size):
        self._delegate.update_width(size)
