import time
import html
import jinja2
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QDesktopServices

from chat.channel_widget import ChannelWidget
from chat.chatter_model import ChatterModel, ChatterEventFilter, \
    ChatterItemDelegate, ChatterSortFilterModel, ChatterFormat
from chat.chatter_menu import ChatterMenu
from model.chat.channel import ChannelType
from model.chat.chatline import ChatLineType
from util.gameurl import GameUrl
from util.magic_dict import MagicDict
from util import irc_escape
from downloadManager import DownloadRequest


class ChannelView(QObject):
    privmsg_requested = pyqtSignal(str)

    def __init__(self, channel, controller, widget, channel_tab,
                 chatter_list_view, lines_view):
        QObject.__init__(self)
        self._channel = channel
        self._controller = controller
        self._chatter_list_view = chatter_list_view
        self._lines_view = lines_view
        self.widget = widget
        self._channel_tab = channel_tab

        self.widget.line_typed.connect(self._at_line_typed)
        self._chatter_list_view.double_clicked.connect(
            self._at_chatter_double_clicked)
        if self._channel.id_key.type == ChannelType.PRIVATE:
            self.widget.show_chatter_list(False)

        self._channel.added_chatter.connect(self._update_chatter_count)
        self._channel.removed_chatter.connect(self._update_chatter_count)
        self._update_chatter_count()

    def _update_chatter_count(self):
        text = "{} users (type to filter)".format(len(self._channel.chatters))
        self.widget.set_nick_edit_label(text)

    @classmethod
    def build(cls, channel, controller, channel_tab, **kwargs):
        chat_css_template = ChatLineCssTemplate.build(**kwargs)
        widget = ChannelWidget.build(channel, chat_css_template, **kwargs)
        lines_view = ChatAreaView.build(channel, widget, channel_tab, **kwargs)
        chatter_list_view = ChattersView.build(channel, widget, **kwargs)
        return cls(channel, controller, widget, channel_tab, chatter_list_view,
                   lines_view)

    @classmethod
    def builder(cls, controller, **kwargs):
        def make(channel, channel_tab):
            return cls.build(channel, controller, channel_tab, **kwargs)
        return make

    def _at_line_typed(self, line):
        self._controller.send_message(self._channel.id_key, line)

    def _at_chatter_double_clicked(self, data):
        self.privmsg_requested.emit(data.chatter.name)

    def on_switched_to(self):
        self._channel_tab.stop_blinking()


class ChatAreaView:
    def __init__(self, channel, widget, widget_tab, game_runner,
                 metadata_builder, avatar_adder, formatter):
        self._channel = channel
        self._widget = widget
        self._widget_tab = widget_tab
        self._game_runner = game_runner
        self._metadata_builder = metadata_builder
        self._channel.lines.added.connect(self._add_line)
        self._channel.lines.removed.connect(self._remove_lines)
        self._channel.updated.connect(self._at_channel_updated)
        self._widget.url_clicked.connect(self._at_url_clicked)
        self._widget.css_reloaded.connect(self._at_css_reloaded)
        self._meta_lines = []
        self._avatar_adder = avatar_adder
        self._formatter = formatter

        self._set_topic(self._channel.topic)

    @classmethod
    def build(cls, channel, widget, widget_tab, game_runner, **kwargs):
        metadata_builder = ChatLineMetadata.builder(**kwargs)
        avatar_adder = ChatAvatarPixAdder.build(widget, **kwargs)
        formatter = ChatLineFormatter.build(**kwargs)
        return cls(channel, widget, widget_tab, game_runner, metadata_builder,
                   avatar_adder, formatter)

    def _add_line(self):
        line = self._channel.lines[-1]
        data = self._metadata_builder(line, self._channel)
        if data.meta.player.avatar.url:
            self._avatar_adder.add_avatar(data.meta.player.avatar.url())
        self._meta_lines.append(data)
        text = self._formatter.format(data)
        self._widget.append_line(text)
        self._blink_if_needed(data)

    def _remove_lines(self, number):
        del self._meta_lines[0:number]
        self._widget.remove_lines(number)

    def _at_channel_updated(self, new, old):
        if new.topic != old.topic:
            self._set_topic(new.topic)

    def _set_topic(self, topic):
        self._widget.set_topic(self._format_topic(topic))

    def _format_topic(self, topic):
        # FIXME - use CSS for this
        fmt = ("<style>a{{color:cornflowerblue}}</style>" +
               "<b><font color=white>{}</font></b>")
        return fmt.format(irc_escape(topic))

    def _at_url_clicked(self, url):
        if not GameUrl.is_game_url(url):
            QDesktopServices.openUrl(url)
            return
        try:
            gurl = GameUrl.from_url(url)
        except ValueError:
            return
        self._game_runner.run_game_from_url(gurl)

    def _should_blink(self, data):
        if not self._widget.hidden:
            return False
        if data.line.type is ChatLineType.INFO:
            return False
        if self._channel.id_key.type == ChannelType.PRIVATE:
            return True
        if data.meta.mentions_me and data.meta.mentions_me():
            return True
        return False

    def _blink_if_needed(self, data):
        if not self._should_blink(data):
            return
        self._widget_tab.start_blinking()

    def _at_css_reloaded(self):
        self._widget.clear_chat()
        for line in self._meta_lines:
            text = self._formatter.format(line)
            self._widget.append_line(text)


class ChatAvatarPixAdder:
    def __init__(self, widget, avatar_dler):
        self._avatar_dler = avatar_dler
        self._widget = widget
        self._requests = {}

    @classmethod
    def build(cls, widget, avatar_dler, **kwargs):
        return cls(widget, avatar_dler)

    def add_avatar(self, url):
        avatar_pix = self._avatar_dler.avatars.get(url, None)
        if avatar_pix is not None:
            self._add_avatar_resource(url, avatar_pix)
        elif url not in self._requests:
            req = DownloadRequest()
            req.done.connect(self._add_avatar_resource)
            self._requests[url] = req
            self._avatar_dler.download_avatar(url, req)

    def _add_avatar_resource(self, url, pix):
        if url in self._requests:
            del self._requests[url]
        self._widget.add_avatar_resource(url, pix)


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
        cmeta.name = cc.chatter.name

    def _player_metadata(self, player):
        if player is None:
            return
        self.meta.put("player")
        self.meta.player.clan = player.clan
        self.meta.player.id = player.id
        self._avatar_metadata(player.avatar)

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

    def _avatar_metadata(self, ava):
        if ava is None:
            return
        tip = ava.get("tooltip", "")
        url = ava.get("url", None)

        self.meta.player.put("avatar")
        self.meta.player.avatar.tip = tip
        if url is not None:
            self.meta.player.avatar.url = url


class ChatLineCssTemplate(QObject):
    changed = pyqtSignal()

    def __init__(self, theme, player_colors):
        QObject.__init__(self)
        self._player_colors = player_colors
        self._player_colors.changed.connect(self._reload_css)
        self._load_template(theme)

    @classmethod
    def build(cls, theme, player_colors, **kwargs):
        return cls(theme, player_colors)

    def _load_template(self, theme):
        self._env = jinja2.Environment()
        template_str = theme.readfile("chat/channel.css")
        self._template = self._env.from_string(template_str)
        self._reload_css()

    def _reload_css(self):
        colors = self._player_colors.colors
        if self._player_colors.colored_nicknames:
            random_colors = self._player_colors.random_colors
        else:
            random_colors = None
        self.css = self._template.render(colors=colors,
                                         random_colors=random_colors)
        self.changed.emit()


class ChatLineFormatter:
    def __init__(self, theme, player_colors):
        self._set_theme(theme)
        self._player_colors = player_colors
        self._last_timestamp = None

    @classmethod
    def build(cls, theme, player_colors, **kwargs):
        return cls(theme, player_colors)

    def _set_theme(self, theme):
        self._chatline_template = theme.readfile("chat/chatline.qhtml")
        self._avatar_template = theme.readfile("chat/chatline_avatar.qhtml")

    def _line_tags(self, data):
        line = data.line
        meta = data.meta
        if line.type == ChatLineType.NOTICE:
            yield "notice"
        if line.type == ChatLineType.ACTION:
            yield "action"
        if line.type == ChatLineType.INFO:
            yield "info"
        if meta.chatter:
            yield "chatter"
            if meta.chatter.is_mod and meta.chatter.is_mod():
                yield "mod"
            name = meta.chatter.name()
            id_ = meta.player.id() if meta.player.id else None
            yield ("randomcolor-{}".format(
                   self._player_colors.get_random_color_index(id_, name)))
        if meta.player:
            yield "player"
        if meta.is_friend and meta.is_friend():
            yield "friend"
        if meta.is_foe and meta.is_foe():
            yield "foe"
        if meta.is_me and meta.is_me():
            yield "me"
        if meta.is_clannie and meta.is_clannie():
            yield "clannie"
        if meta.mentions_me and meta.mentions_me():
            yield "mentions_me"
        if meta.player.avatar and meta.player.avatar():
            yield "avatar"

    def format(self, data):
        tags = " ".join(self._line_tags(data))
        avatar = self._avatar(data)

        if self._check_timestamp(data.line.time):
            stamp = time.strftime('%H:%M', time.localtime(data.line.time))
        else:
            stamp = ""

        return self._chatline_template.format(
            time=stamp,
            sender=self._sender_name(data),
            text=irc_escape(data.line.text),
            avatar=avatar,
            tags=tags)

    def _avatar(self, data):
        if data.line.type == ChatLineType.INFO:
            return ""
        if not data.meta.player.avatar.url:
            return ""
        ava_meta = data.meta.player.avatar
        avatar_url = ava_meta.url()
        avatar_tip = ava_meta.tip() if ava_meta.tip else ""
        return self._avatar_template.format(url=avatar_url, tip=avatar_tip)

    def _sender_name(self, data):
        mtype = data.line.type
        sender = ChatterFormat.name(data.line.sender, data.meta.player.clan())
        sender = html.escape(sender)
        if mtype not in [ChatLineType.ACTION, ChatLineType.INFO]:
            sender += ":&nbsp;"
        return sender

    def _check_timestamp(self, stamp):
        local = time.localtime(stamp)
        new_stamp = (self._last_timestamp is None or
                     local.tm_hour != self._last_timestamp.tm_hour or
                     local.tm_min != self._last_timestamp.tm_min)
        if new_stamp:
            self._last_timestamp = local
        return new_stamp


class ChattersViewParameters(QObject):
    updated = pyqtSignal()

    def __init__(self, me, player_colors):
        QObject.__init__(self)
        self._me = me
        self._me.playerChanged.connect(self.updated.emit)
        self._me.clan_changed.connect(self.updated.emit)
        self._player_colors = player_colors
        self._player_colors.changed.connect(self.updated.emit)

    @classmethod
    def build(cls, me, player_colors, **kwargs):
        return cls(me, player_colors)


class ChattersView:
    def __init__(self, widget, delegate, model, event_filter, view_parameters):
        self.delegate = delegate
        self.model = model
        self.event_filter = event_filter
        self._view_parameters = view_parameters
        self.widget = widget

        widget.set_chatter_delegate(self.delegate)
        widget.set_chatter_model(self.model)
        widget.set_chatter_event_filter(self.event_filter)
        widget.chatter_list_resized.connect(self._at_chatter_list_resized)
        view_parameters.updated.connect(self._at_view_parameters_updated)

    def _at_chatter_list_resized(self, size):
        self.delegate.update_width(size)

    def _at_view_parameters_updated(self):
        self.model.invalidate_items()

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
        view_parameters = ChattersViewParameters.build(**kwargs)

        return cls(widget, delegate, sort_filter_model, event_filter,
                   view_parameters)

    @property
    def double_clicked(self):
        return self.event_filter.double_clicked
