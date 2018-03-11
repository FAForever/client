from PyQt5.QtCore import QObject, pyqtSignal

from chat.channel_widget import ChannelWidget
from chat.chatter_model import ChatterModel, ChatterEventFilter, \
    ChatterItemDelegate, ChatterSortFilterModel
from chat.chatter_menu import ChatterMenu
from model.chat.channel import ChannelType
from util.magic_dict import MagicDict


class ChannelView(QObject):
    privmsg_requested = pyqtSignal(str)

    def __init__(self, channel, controller, widget, chatter_list_view,
                 lines_view):
        QObject.__init__(self)
        self._channel = channel
        self._controller = controller
        self._chatter_list_view = chatter_list_view
        self._lines_view = lines_view
        self.widget = widget

        self.widget.line_typed.connect(self._at_line_typed)
        self._chatter_list_view.double_clicked.connect(
            self._at_chatter_double_clicked)
        if self._channel.id_key.type == ChannelType.PRIVATE:
            self.widget.show_chatter_list(False)

    @classmethod
    def build(cls, channel, controller, **kwargs):
        widget = ChannelWidget.build(channel, **kwargs)
        lines_view = ChatAreaView.build(channel, widget, **kwargs)
        chatter_list_view = ChattersView.build(channel, widget, **kwargs)
        return cls(channel, controller, widget, chatter_list_view, lines_view)

    @classmethod
    def builder(cls, controller, **kwargs):
        def make(channel):
            return cls.build(channel, controller, **kwargs)
        return make

    def _at_line_typed(self, line):
        self._controller.send_message(self._channel.id_key, line)

    def _at_chatter_double_clicked(self, data):
        self.privmsg_requested.emit(data.chatter.name)


class ChatAreaView:
    def __init__(self, channel, widget, metadata_builder):
        self._channel = channel
        self._widget = widget
        self._metadata_builder = metadata_builder
        self._channel.lines.added.connect(self._add_line)
        self._meta_lines = []

    @classmethod
    def build(cls, channel, widget, **kwargs):
        metadata_builder = ChatLineMetadata.builder(**kwargs)
        return cls(channel, widget, metadata_builder)

    def _add_line(self, number):
        for line in self._channel.lines[-number:]:
            meta = self._metadata_builder(line, self._channel)
            self._meta_lines.append(meta)
            self._widget.append_line(meta)


class ChatLineMetadata:
    def __init__(self, line, channel, channelchatterset, me, user_relations):
        self.line = line
        self._make_metadata(channel, channelchatterset, me, user_relations)

    @classmethod
    def builder(cls, channelchatterset, me, user_relations, **kwargs):
        def make(line, channel):
            return cls(line, channel, channelchatterset, me,
                       user_relations.model)
        return make

    def _make_metadata(self, channel, channelchatterset, me, user_relations):
        self.meta = MagicDict()
        cc = channelchatterset.get((channel.id_key, self.line.sender), None)
        chatter = None
        player = None
        if cc is not None:
            chatter = cc.chatter
            player = chatter.player

        self._chatter_metadata(cc, chatter)
        self._player_metadata(player)
        self._relation_metadata(chatter, player, me, user_relations)
        self._mention_metadata(me)

    def _chatter_metadata(self, cc, chatter):
        if cc is None:
            return
        cmeta = self.meta.put("chatter")
        cmeta.is_mod = cc.is_mod()

    def _player_metadata(self, player):
        if player is None:
            return
        self.meta.put("player")

    def _relation_metadata(self, chatter, player, me, user_relations):
        name = None if chatter is None else chatter.name
        id_ = None if player is None else player.id
        self.meta.is_friend = user_relations.is_friend(id_, name)
        self.meta.is_foe = user_relations.is_foe(id_, name)
        self.meta.is_me = me.player is not None and me.player.login == name
        self.meta.is_clannie = me.is_clannie(id_)

    def _mention_metadata(self, me):
        self.meta.mentions_me = (me.login is not None and
                                 me.login in self.line.text)


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
    def build(cls, channel, widget, user_relations, **kwargs):
        model = ChatterModel.build(
            channel, relation_trackers=user_relations.trackers, **kwargs)
        sort_filter_model = ChatterSortFilterModel.build(
            model, user_relations=user_relations.model, **kwargs)

        chatter_menu = ChatterMenu.build(**kwargs)
        delegate = ChatterItemDelegate.build(**kwargs)
        event_filter = ChatterEventFilter.build(delegate, chatter_menu,
                                                **kwargs)

        return cls(widget, delegate, sort_filter_model, event_filter)

    @property
    def double_clicked(self):
        return self.event_filter.double_clicked
