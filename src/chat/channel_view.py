import html
import time

import jinja2
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QDesktopServices

from chat.channel_tab import TabInfo
from chat.channel_widget import ChannelWidget
from chat.chatter_menu import ChatterMenu
from chat.chatter_model import (
    ChatterEventFilter,
    ChatterFormat,
    ChatterItemDelegate,
    ChatterLayout,
    ChatterLayoutElements,
    ChatterModel,
    ChatterSortFilterModel,
)
from downloadManager import DownloadRequest
from model.chat.channel import ChannelType
from model.chat.chatline import ChatLineType
from util import irc_escape
from util.gameurl import GameUrl


class ChannelView:
    def __init__(
        self, channel, controller, widget, channel_tab,
        chatter_list_view, lines_view,
    ):
        self._channel = channel
        self._controller = controller
        self._chatter_list_view = chatter_list_view
        self._lines_view = lines_view
        self.widget = widget
        self._channel_tab = channel_tab

        self.widget.line_typed.connect(self._at_line_typed)
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
        chatter_list_view = ChattersView.build(
            channel, widget, controller, **kwargs
        )
        return cls(
            channel, controller, widget, channel_tab, chatter_list_view,
            lines_view,
        )

    @classmethod
    def builder(cls, controller, **kwargs):
        def make(channel, channel_tab):
            return cls.build(channel, controller, channel_tab, **kwargs)
        return make

    def _at_line_typed(self, line):
        self._controller.send_message(self._channel.id_key, line)

    def on_shown(self):
        self._channel_tab.info = TabInfo.IDLE


class ChatAreaView:
    def __init__(
        self, channel, widget, widget_tab, game_runner, avatar_adder,
        formatter,
    ):
        self._channel = channel
        self._widget = widget
        self._widget_tab = widget_tab
        self._game_runner = game_runner
        self._channel.lines.added.connect(self._add_line)
        self._channel.lines.removed.connect(self._remove_lines)
        self._channel.updated.connect(self._at_channel_updated)
        self._widget.url_clicked.connect(self._at_url_clicked)
        self._widget.css_reloaded.connect(self._at_css_reloaded)
        self._avatar_adder = avatar_adder
        self._formatter = formatter

        self._set_topic(self._channel.topic)

    @classmethod
    def build(cls, channel, widget, widget_tab, game_runner, **kwargs):
        avatar_adder = ChatAvatarPixAdder.build(widget, **kwargs)
        formatter = ChatLineFormatter.build(**kwargs)
        return cls(
            channel, widget, widget_tab, game_runner, avatar_adder, formatter,
        )

    def _add_line(self):
        data = self._channel.lines[-1]
        if data.meta.player.avatar.url:
            self._avatar_adder.add_avatar(data.meta.player.avatar.url())
        text = self._formatter.format(data)
        self._widget.append_line(text)
        self._set_tab_info(data)

    def _remove_lines(self, number):
        self._widget.remove_lines(number)

    def _at_channel_updated(self, new, old):
        if new.topic != old.topic:
            self._set_topic(new.topic)

    def _set_topic(self, topic):
        self._widget.set_topic(self._format_topic(topic))

    def _format_topic(self, topic):
        # FIXME - use CSS for this
        fmt = (
            "<style>a{{color:cornflowerblue}}</style>"
            "<b><font color=white>{}</font></b>"
        )
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

    def _set_tab_info(self, data):
        self._widget_tab.info = self._tab_info(data)

    def _tab_info(self, data):
        if not self._widget.hidden:
            return TabInfo.IDLE
        if self._line_is_important(data):
            return TabInfo.IMPORTANT
        return TabInfo.NEW_MESSAGES

    def _line_is_important(self, data):
        if data.line.type in [
            ChatLineType.INFO, ChatLineType.ANNOUNCEMENT, ChatLineType.RAW,
        ]:
            return False
        if self._channel.id_key.type == ChannelType.PRIVATE:
            return True
        if data.meta.mentions_me and data.meta.mentions_me():
            return True
        return False

    def _at_css_reloaded(self):
        self._widget.clear_chat()
        for line in self._channel.lines:
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


class ChatLineCssTemplate(QObject):
    changed = pyqtSignal()

    def __init__(self, theme, player_colors):
        QObject.__init__(self)
        self._player_colors = player_colors
        self._theme = theme
        self._player_colors.changed.connect(self._reload_css)
        self._theme.stylesheets_reloaded.connect(self._load_template)
        self._load_template()

    @classmethod
    def build(cls, theme, player_colors, **kwargs):
        return cls(theme, player_colors)

    def _load_template(self):
        self._env = jinja2.Environment()
        template_str = self._theme.readfile("chat/channel.css")
        self._template = self._env.from_string(template_str)
        self._reload_css()

    def _reload_css(self):
        colors = self._player_colors.colors
        if self._player_colors.colored_nicknames:
            random_colors = self._player_colors.random_colors
        else:
            random_colors = None
        self.css = self._template.render(
            colors=colors,
            random_colors=random_colors,
        )
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
        if line.type == ChatLineType.ANNOUNCEMENT:
            yield "announcement"
            return      # Let announcements decorate themselves
        if line.type == ChatLineType.RAW:
            yield "raw"
            return      # Ditto
        if meta.chatter:
            yield "chatter"
            if meta.chatter.is_mod and meta.chatter.is_mod():
                yield "mod"
            name = meta.chatter.name()
            id_ = meta.player.id() if meta.player.id else None
            yield (
                "randomcolor-{}".format(
                    self._player_colors.get_random_color_index(id_, name),
                )
            )
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

        text = data.line.text
        if data.line.type not in [ChatLineType.ANNOUNCEMENT, ChatLineType.RAW]:
            text = irc_escape(text)
        if data.line.type == ChatLineType.RAW:
            return text

        return self._chatline_template.format(
            time=stamp,
            sender=self._sender_name(data),
            text=text,
            avatar=avatar,
            tags=tags,
        )

    def _avatar(self, data):
        if data.line.type in [
            ChatLineType.INFO, ChatLineType.ANNOUNCEMENT, ChatLineType.RAW,
        ]:
            return ""
        if not data.meta.player.avatar.url:
            return ""
        ava_meta = data.meta.player.avatar
        avatar_url = ava_meta.url()
        avatar_tip = ava_meta.tip() if ava_meta.tip else ""
        return self._avatar_template.format(url=avatar_url, tip=avatar_tip)

    def _sender_name(self, data):
        if data.line.sender is None:
            return ""
        mtype = data.line.type
        sender = ChatterFormat.name(data.line.sender, data.meta.player.clan())
        sender = html.escape(sender)
        if mtype in [ChatLineType.MESSAGE, ChatLineType.NOTICE]:
            sender += ":&nbsp;"
        return sender

    def _check_timestamp(self, stamp):
        local = time.localtime(stamp)
        new_stamp = (
            self._last_timestamp is None
            or local.tm_hour != self._last_timestamp.tm_hour
            or local.tm_min != self._last_timestamp.tm_min
        )
        if new_stamp:
            self._last_timestamp = local
        return new_stamp


class ChattersViewParameters(QObject):
    updated = pyqtSignal()

    def __init__(self, me, player_colors):
        QObject.__init__(self)
        self._me = me
        self._me.playerChanged.connect(self._updated)
        self._me.clan_changed.connect(self._updated)
        self._player_colors = player_colors
        self._player_colors.changed.connect(self._updated)

    def _updated(self):
        self.updated.emit()

    @classmethod
    def build(cls, me, player_colors, **kwargs):
        return cls(me, player_colors)


class ChattersView:
    def __init__(
        self, widget, chatter_layout, delegate, model, controller,
        event_filter, double_click_handler, view_parameters,
    ):
        self.chatter_layout = chatter_layout
        self.delegate = delegate
        self.model = model
        self._controller = controller
        self.event_filter = event_filter
        self._double_click_handler = double_click_handler
        self._view_parameters = view_parameters
        self.widget = widget

        widget.set_chatter_delegate(self.delegate)
        widget.set_chatter_model(self.model)
        widget.set_chatter_event_filter(self.event_filter)
        widget.chatter_list_resized.connect(self._at_chatter_list_resized)
        view_parameters.updated.connect(self._at_view_parameters_updated)
        self.event_filter.double_clicked.connect(
            self._double_click_handler.handle,
        )

    def _at_chatter_list_resized(self, size):
        self.delegate.update_width(size)

    def _at_view_parameters_updated(self):
        self.model.invalidate_items()

    @classmethod
    def build(cls, channel, widget, controller, user_relations, **kwargs):
        model = ChatterModel.build(
            channel, relation_trackers=user_relations.trackers, **kwargs
        )
        sort_filter_model = ChatterSortFilterModel.build(
            model, user_relations=user_relations.model, **kwargs
        )

        chatter_layout = ChatterLayout.build(**kwargs)
        chatter_menu = ChatterMenu.build(**kwargs)
        delegate = ChatterItemDelegate.build(chatter_layout, **kwargs)
        event_filter = ChatterEventFilter.build(
            chatter_layout, delegate, chatter_menu, **kwargs
        )
        double_click_handler = ChatterDoubleClickHandler.build(
            controller, **kwargs
        )
        view_parameters = ChattersViewParameters.build(**kwargs)

        return cls(
            widget, chatter_layout, delegate, sort_filter_model,
            controller, event_filter, double_click_handler, view_parameters,
        )


class ChatterDoubleClickHandler:
    def __init__(self, controller, game_runner):
        self._controller = controller
        self._game_runner = game_runner

    @classmethod
    def build(cls, controller, game_runner, **kwargs):
        return cls(controller, game_runner)

    def handle(self, data, elem):
        if elem == ChatterLayoutElements.STATUS:
            self._game_action(data)
        else:
            self._privmsg(data)

    def _privmsg(self, data):
        self._controller.join_private_channel(data.chatter.name)

    def _game_action(self, data):
        game = data.game
        player = data.player
        if game is None or player is None:
            return
        self._game_runner.run_game_with_url(game, player.id)
