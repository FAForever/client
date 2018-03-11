from chat.channel_widget import ChannelWidget
from chat.chatter_model import ChatterModel, ChatterEventFilter, \
    ChatterItemDelegate, ChatterSortFilterModel
from chat.chatter_menu import ChatterMenu


class ChannelView:
    def __init__(self, channel, controller, widget, chatter_list_view):
        self._channel = channel
        self._controller = controller
        self._chatter_list_view = chatter_list_view
        self.widget = widget

        self.widget.line_typed.connect(self._at_line_typed)
        channel.lines.added.connect(self._add_line)

    @classmethod
    def build(cls, channel, controller, **kwargs):
        widget = ChannelWidget.build(channel, **kwargs)
        chatter_list_view = ChattersView.build(channel, widget, **kwargs)
        return cls(channel, controller, widget, chatter_list_view)

    @classmethod
    def builder(cls, controller, **kwargs):
        def make(channel):
            return cls.build(channel, controller, **kwargs)
        return make

    def _add_line(self, number):
        for line in self._channel.lines[-number:]:
            self.widget.append_line(line)

    def _at_line_typed(self, line):
        self._controller.send_message(self._channel.id_key, line)


class ChattersView:
    def __init__(self, widget, delegate, model, event_filter):
        self.delegate = delegate
        self.model = model
        self.event_filter = event_filter
        self.widget = widget

        widget.set_chatter_delegate(self.delegate)
        widget.set_chatter_model(self.model)
        widget.set_chatter_event_filter(self.event_filter)
        widget.chatter_list_resized.connect(self.at_chatter_list_resized)

    def at_chatter_list_resized(self, size):
        self.delegate.update_width(size)

    @classmethod
    def build(cls, channel, widget, **kwargs):
        chatter_menu = ChatterMenu.build(**kwargs)
        delegate = ChatterItemDelegate.build(**kwargs)
        event_filter = ChatterEventFilter.build(delegate, chatter_menu,
                                                **kwargs)
        model = ChatterModel.build(channel, **kwargs)
        sort_filter_model = ChatterSortFilterModel.build(model, **kwargs)
        return cls(widget, delegate, sort_filter_model, event_filter)
