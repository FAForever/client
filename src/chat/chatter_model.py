from enum import Enum, IntEnum
from PyQt5.QtCore import QObject, QRectF, QSortFilterProxyModel, Qt, \
    pyqtSignal
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtGui import QIcon, QColor
from chat.chatter_model_item import ChatterModelItem
from chat.gameinfo import SensitiveMapInfoChecker
from fa import maps
from model.game import GameState
import util
from util.qt_list_model import QtListModel


class ChatterModel(QtListModel):
    def __init__(self, channel, item_builder):
        QtListModel.__init__(self, item_builder)
        self._channel = channel

        if self._channel is not None:
            self._channel.added_chatter.connect(self.add_chatter)
            self._channel.removed_chatter.connect(self.remove_chatter)

        for chatter in self._channel.chatters:
            self.add_chatter(chatter)

    @classmethod
    def build(cls, channel, **kwargs):
        builder = ChatterModelItem.builder(**kwargs)
        return cls(channel, builder)

    def add_chatter(self, chatter):
        self._add_item(chatter, chatter.id_key)

    def remove_chatter(self, chatter):
        self._remove_item(chatter.id_key)

    def clear_chatters(self):
        self._clear_items()

    def invalidate_items(self):
        start = self.index(0)
        end = self.index(len(self._itemlist) - 1)
        self.dataChanged.emit(start, end)


class ChatterRank(IntEnum):
    FRIEND_ON_TOP = -1
    ELEVATED = 0
    FRIEND = 1
    CLANNIE = 2
    USER = 3
    NONPLAYER = 4
    FOE = 5


class ChatterSortFilterModel(QSortFilterProxyModel):
    def __init__(self, model, me, user_relations, chat_config):
        QSortFilterProxyModel.__init__(self)
        self._me = me
        self._user_relations = user_relations
        self._chat_config = chat_config
        self._chat_config.updated.connect(self._check_sort_changed)
        self.setSourceModel(model)
        self.sort(0)

    @classmethod
    def build(cls, model, me, user_relations, chat_config, **kwargs):
        return cls(model, me, user_relations, chat_config)

    def lessThan(self, leftIndex, rightIndex):
        source = self.sourceModel()
        left = source.data(leftIndex, Qt.DisplayRole)
        right = source.data(rightIndex, Qt.DisplayRole)

        comp_list = [self._lt_me, self._lt_rank, self._lt_alphabetical]
        for lt in comp_list:
            if lt(left, right):
                return True
            elif lt(right, left):
                return False
        return False

    def _lt_me(self, left, right):
        if self._me.login is None:
            return False
        return (left.chatter.name == self._me.login and
                right.chatter.name != self._me.login)

    def _lt_rank(self, left, right):
        left_rank = self._get_user_rank(left)
        right_rank = self._get_user_rank(right)
        return left_rank < right_rank

    def _lt_alphabetical(self, left, right):
        return left.chatter.name.lower() < right.chatter.name.lower()

    def _get_user_rank(self, item):
        pid = item.player.id if item.player is not None else None
        name = item.chatter.name
        is_friend = self._user_relations.is_friend(pid, name)
        if self._chat_config.friendsontop and is_friend:
            return ChatterRank.FRIEND_ON_TOP
        if item.cc.is_mod():
            return ChatterRank.ELEVATED
        if is_friend:
            return ChatterRank.FRIEND
        if self._me.is_clannie(pid):
            return ChatterRank.CLANNIE
        if self._user_relations.is_foe(pid, name):
            return ChatterRank.FOE
        if item.player is not None:
            return ChatterRank.USER
        return ChatterRank.NONPLAYER

    def filterAcceptsRow(self, row, parent):
        source = self.sourceModel()
        index = source.index(row, 0, parent)
        if not index.isValid():
            return False
        data = source.data(index, Qt.DisplayRole)
        displayed_name = ChatterFormat.chatter_name(data.chatter)
        return self.filterRegExp().indexIn(displayed_name) != -1

    def _check_sort_changed(self, option):
        if option == "friendsontop":
            self.invalidate()

    def invalidate_items(self):
        self.sourceModel().invalidate_items()


# TODO - place in some separate file?
class ChatterFormat:
    @classmethod
    def name(cls, chatter, clan):
        if clan is not None:
            return "[{}]{}".format(clan, chatter)
        else:
            return chatter

    @classmethod
    def chatter_name(cls, chatter):
        clan = None if chatter.player is None else chatter.player.clan
        return cls.name(chatter.name, clan)


class ChatterItemFormatter:
    def __init__(self, avatars, player_colors, info_hider):
        self._avatars = avatars
        self._player_colors = player_colors
        self._info_hider = info_hider

    @classmethod
    def build(cls, avatar_dler, player_colors, **kwargs):
        info_hider = SensitiveMapInfoChecker.build(**kwargs)
        return cls(avatar_dler, player_colors, info_hider)

    def map_icon(self, data):
        game = data.game
        if game is None or game.closed():
            should_hide_info = False
        else:
            should_hide_info = self._info_hider.has_sensitive_data(game)
        if should_hide_info:
            return None

        name = data.map_name()
        return None if name is None else maps.preview(name)

    def chatter_name(self, data):
        return ChatterFormat.chatter_name(data.chatter)

    def chatter_color(self, data):
        pid = -1 if data.player is None else data.player.id
        colors = self._player_colors
        cc = data.cc
        if cc.is_mod():
            return colors.get_mod_color(pid, data.chatter.name)
        else:
            return colors.get_user_color(pid, data.chatter.name)

    def chatter_status(self, data):
        game = data.game
        if game is None or game.closed():
            return "none"
        if game.state == GameState.OPEN:
            if game.host == data.chatter.name:
                return "host"
            return "lobby"
        if game.state == GameState.PLAYING:
            if game.has_live_replay:
                return "playing"
            return "playing5"
        return "unknown"

    def chatter_rank(self, data):
        if data.player is None:
            return "civilian"
        league = data.player.league
        if league is None or "league" not in league:
            return "newplayer"
        return league["league"]

    def chatter_avatar_icon(self, data):
        avatar_url = data.avatar_url()
        if avatar_url is None:
            return None
        if avatar_url not in self._avatars.avatars:
            return
        return QIcon(self._avatars.avatars[avatar_url])

    def chatter_country(self, data):
        if data.player is None:
            return None
        country = data.player.country
        if country is None or country == '':
            return '__'
        return country

    def rank_tooltip(self, data):
        if data.player is None:
            return "IRC User"
        player = data.player
        # chr(0xB1) = +-
        formatting = ("Global Rating: {} ({} Games) [{}\xb1{}]\n"
                      "Ladder Rating: {} [{}\xb1{}]")
        tooltip_str = formatting.format((int(player.rating_estimate)),
                                        player.number_of_games,
                                        int(player.rating_mean),
                                        int(player.rating_deviation),
                                        int(player.ladder_estimate()),
                                        int(player.ladder_rating_mean),
                                        int(player.ladder_rating_deviation))
        league = player.league
        if league is not None and "division" in league:
            tooltip_str = "Division : {}\n{}".format(league["division"],
                                                     tooltip_str)
        return tooltip_str

    def status_tooltip(self, data):
        # Status tooltip handling
        game = data.game
        if game is None or game.closed():
            return "Idle"

        if self._info_hider.has_sensitive_data(game):
            game_map = "<i>[delayed reveal]</i>"
            game_title = "<i>[delayed reveal]</i>"
        else:
            game_map = game.mapdisplayname
            game_title = game.title

        private_str = " (private)" if game.password_protected else ""
        if game.state == GameState.PLAYING and not game.has_live_replay:
            delay_str = " - LIVE DELAY (5 Min)"
        else:
            delay_str = ""

        head_str = ""
        if game.state == GameState.OPEN:
            if game.host == data.player.login:
                head_str = "Hosting{private} game</b>"
            else:
                head_str = "In{private} Lobby</b> (host {host})"
        elif game.state == GameState.PLAYING:
            head_str = "Playing</b>{delay}"
        header = head_str.format(private=private_str, delay=delay_str,
                                 host=game.host)

        formatting = ("<b>{}<br/>"
                      "title: {}<br/>"
                      "mod: {}<br/>"
                      "map: {}<br/>"
                      "players: {} / {}<br/>"
                      "id: {}")

        game_str = formatting.format(header, game_title, game.featured_mod,
                                     game_map, game.num_players,
                                     game.max_players, game.uid)
        return game_str

    def avatar_tooltip(self, data):
        try:
            return data.player.avatar["tooltip"]
        except (TypeError, AttributeError, KeyError):
            return None

    def map_tooltip(self, data):
        if data.game is None:
            return None
        if self._info_hider.has_sensitive_data(data.game):
            return "<i>[delayed reveal]</i>"
        return data.game.mapdisplayname

    def country_tooltip(self, data):
        return self.chatter_country(data)

    def nick_tooltip(self, data):
        return self.country_tooltip(data)


class ChatterItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, layout, formatter):
        QtWidgets.QStyledItemDelegate.__init__(self)
        self.layout = layout
        self._formatter = formatter

    @classmethod
    def build(cls, layout, **kwargs):
        formatter = ChatterItemFormatter.build(**kwargs)
        return cls(layout, formatter)

    def update_width(self, size):
        current_size = self.layout.size
        if size.width() != current_size.width():
            current_size.setWidth(size.width())
            self.layout.size = current_size

    def paint(self, painter, option, index):
        painter.save()

        data = index.data()

        self._draw_clear_option(painter, option)
        self._handle_highlight(painter, option)

        painter.translate(option.rect.left(), option.rect.top())

        Elems = ChatterLayoutElements
        draw = {
            Elems.NICK: self._draw_nick,
            Elems.STATUS: self._draw_status,
            Elems.MAP: self._draw_map,
            Elems.RANK: self._draw_rank,
            Elems.AVATAR: self._draw_avatar,
            Elems.COUNTRY: self._draw_country
        }
        for item in self.layout.visible_items():
            draw[item](painter, data)

        painter.restore()

    def _draw_clear_option(self, painter, option):
        option.icon = QtGui.QIcon()
        option.text = ""
        option.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem,
                                          option, painter, option.widget)

    def _handle_highlight(self, painter, option):
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight)

    def _draw_nick(self, painter, data):
        text = self._formatter.chatter_name(data)
        color = QColor(self._formatter.chatter_color(data))
        clip = QRectF(self.layout.sizes[ChatterLayoutElements.NICK])
        text = self._get_elided_text(painter, text, clip.width())

        painter.save()
        pen = painter.pen()
        pen.setColor(color)
        painter.setPen(pen)

        painter.drawText(clip, Qt.AlignLeft | Qt.AlignVCenter, text)

        painter.restore()

    def _get_elided_text(self, painter, text, width):
        metrics = painter.fontMetrics()
        return metrics.elidedText(text, Qt.ElideRight, width)

    def _draw_status(self, painter, data):
        status = self._formatter.chatter_status(data)
        icon = util.THEME.icon("chat/status/{}.png".format(status))
        self._draw_icon(painter, icon, ChatterLayoutElements.STATUS)

    # TODO - handle optionality of maps
    def _draw_map(self, painter, data):
        icon = self._formatter.map_icon(data)
        if not icon:
            return
        self._draw_icon(painter, icon, ChatterLayoutElements.MAP)

    def _draw_rank(self, painter, data):
        rank = self._formatter.chatter_rank(data)
        icon = util.THEME.icon("chat/rank/{}.png".format(rank))
        self._draw_icon(painter, icon, ChatterLayoutElements.RANK)

    def _draw_avatar(self, painter, data):
        icon = self._formatter.chatter_avatar_icon(data)
        if not icon:
            return
        self._draw_icon(painter, icon, ChatterLayoutElements.AVATAR)

    def _draw_country(self, painter, data):
        country = self._formatter.chatter_country(data)
        if country is None:
            return
        icon = util.THEME.icon("chat/countries/{}.png".format(country.lower()))
        self._draw_icon(painter, icon, ChatterLayoutElements.COUNTRY)

    def _draw_icon(self, painter, icon, element):
        rect = self.layout.sizes[element]
        icon.paint(painter, rect, QtCore.Qt.AlignCenter)

    def sizeHint(self, option, index):
        return self.layout.size

    def get_tooltip(self, data, elem):
        if elem is None:
            return None
        return self._tooltip(data, elem)

    def _tooltip(self, data, item):
        if item == ChatterLayoutElements.RANK:
            return self._formatter.rank_tooltip(data)
        elif item == ChatterLayoutElements.STATUS:
            return self._formatter.status_tooltip(data)
        elif item == ChatterLayoutElements.AVATAR:
            return self._formatter.avatar_tooltip(data)
        elif item == ChatterLayoutElements.MAP:
            return self._formatter.map_tooltip(data)
        elif item == ChatterLayoutElements.COUNTRY:
            return self._formatter.country_tooltip(data)
        elif item == ChatterLayoutElements.NICK:
            return self._formatter.nick_tooltip(data)


class ChatterLayoutElements(Enum):
    RANK = "rankBox"
    STATUS = "statusBox"
    AVATAR = "avatarBox"
    MAP = "mapBox"
    COUNTRY = "countryBox"
    NICK = "nickBox"


class ChatterLayout(QObject):
    """Provides layout info for delegate using Qt widget layouts."""
    LAYOUT_FILE = "chat/chatter.ui"

    def __init__(self, theme, chat_config):
        QObject.__init__(self)
        self._theme = theme
        self._chat_config = chat_config
        self.sizes = {}
        self.load_layout()
        self._chat_config.updated.connect(self._at_chat_config_updated)
        self._set_visibility()

    @classmethod
    def build(cls, theme, chat_config, **kwargs):
        return cls(theme, chat_config)

    def load_layout(self):
        formc, basec = self._theme.loadUiType(self.LAYOUT_FILE)
        self._form = formc()
        self._base = basec()
        self._form.setupUi(self._base)
        self._size = self._base.size()

    def _at_chat_config_updated(self, setting):
        if setting == "hide_chatter_items":
            self._set_visibility()

    def _set_visibility(self):
        for item in ChatterLayoutElements:
            self._set_visible(item)
        self._update_layout()

    def _set_visible(self, item):
        getattr(self._form, item.value).setVisible(self.is_visible(item))

    def is_visible(self, item):
        return item not in self._chat_config.hide_chatter_items

    def visible_items(self):
        return [i for i in ChatterLayoutElements if self.is_visible(i)]

    @property
    def size(self):
        return self._base.size()

    @size.setter
    def size(self, size):
        self._size = size
        self._update_layout()

    def element_at_point(self, point):
        for elem in ChatterLayoutElements:
            if self.sizes[elem].contains(point) and self.is_visible(elem):
                return elem
        return None

    def _update_layout(self):
        self._base.resize(self._size)
        self._force_layout_recalculation()
        for elem in ChatterLayoutElements:
            self.sizes[elem] = self._get_widget_position(elem.value)

    def _force_layout_recalculation(self):
        layout = self._base.layout()
        layout.update()
        layout.activate()

    def _get_widget_position(self, name):
        widget = getattr(self._form, name)
        size = widget.rect()
        top_left = widget.mapTo(self._base, size.topLeft())
        size.moveTopLeft(top_left)
        return size


class ChatterEventFilter(QObject):
    double_clicked = pyqtSignal(object, object)

    def __init__(self, chatter_layout, tooltip_handler, menu_handler):
        QObject.__init__(self)
        self._chatter_layout = chatter_layout
        self._tooltip_handler = tooltip_handler
        self._menu_handler = menu_handler

    @classmethod
    def build(cls, chatter_layout, tooltip_handler, menu_handler, **kwargs):
        return cls(chatter_layout, tooltip_handler, menu_handler)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.ToolTip:
            return self._handle_tooltip(obj, event)
        elif event.type() == QtCore.QEvent.MouseButtonRelease:
            if event.button() == QtCore.Qt.RightButton:
                return self._handle_context_menu(obj, event)
        elif event.type() == QtCore.QEvent.MouseButtonDblClick:
            if event.button() == QtCore.Qt.LeftButton:
                return self._handle_double_click(obj, event)
        return super().eventFilter(obj, event)

    def _get_data_and_elem(self, widget, event):
        view = widget.parent()
        idx = view.indexAt(event.pos())
        if not idx.isValid():
            return None, None
        item_rect = view.visualRect(idx)
        point = event.pos() - item_rect.topLeft()
        elem = self._chatter_layout.element_at_point(point)
        return idx.data(), elem

    def _handle_tooltip(self, widget, event):
        data, elem = self._get_data_and_elem(widget, event)
        if data is None:
            return False
        tooltip_text = self._tooltip_handler.get_tooltip(data, elem)
        if tooltip_text is None:
            return False

        QtWidgets.QToolTip.showText(event.globalPos(), tooltip_text, widget)
        return True

    def _handle_context_menu(self, widget, event):
        data, elem = self._get_data_and_elem(widget, event)
        if data is None:
            return False

        menu = self._menu_handler.get_context_menu(data, elem)
        menu.popup(QtGui.QCursor.pos())
        return True

    def _handle_double_click(self, widget, event):
        data, elem = self._get_data_and_elem(widget, event)
        if data is None:
            return False
        self.double_clicked.emit(data, elem)
        return True
