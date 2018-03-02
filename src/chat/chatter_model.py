from enum import Enum
from PyQt5.QtCore import QObject, QAbstractListModel, Qt, QModelIndex, \
    QRectF, QPoint
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMenu, QAction
from chat.chatter_model_item import ChatterModelItem
from fa import maps
from model.game import GameState
import util
from chat.chatter_model_item import ChatterModelItem


class ChatterModel(QAbstractListModel):
    def __init__(self, channel, item_builder):
        QAbstractListModel.__init__(self)
        self._channel = channel
        self._itemlist = []
        self._items = {}
        self._item_builder = item_builder

        if self._channel is not None:
            self._channel.added_chatter.connect(self.add_chatter)
            self._channel.removed_chatter.connect(self.remove_chatter)

        for chatter in self._channel.chatters:
            self.add_chatter(chatter)

    @classmethod
    def build(cls, channel, **kwargs):
        builder = ChatterModelItem.builder(**kwargs)
        return cls(channel, builder)

    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self._itemlist):
            return None
        if role != Qt.DisplayRole:
            return None
        return self._itemlist[index.row()]

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self._itemlist)

    def add_chatter(self, chatter):
        assert chatter.id_key not in self._items

        next_index = len(self._itemlist)
        self.beginInsertRows(QModelIndex(), next_index, next_index)

        item = self._item_builder(chatter)
        item.updated.connect(self._at_item_updated)

        self._items[chatter.id_key] = item
        self._itemlist.append(item)

        self.endInsertRows()

    # FIXME - removal is O(n)
    def remove_chatter(self, chatter):
        assert chatter.id_key in self._items

        item = self._items[chatter.id_key]
        item_index = self._itemlist.index(item)
        self.beginRemoveRows(QModelIndex(), item_index, item_index)

        item.updated.disconnect(self._at_item_updated)
        del self._items[chatter.id_key]
        self._itemlist.pop(item_index)
        self.endRemoveRows()

    def clear_chatters(self):
        for data in list(self._itemlist):
            self.remove_chatter(data.chatter)

    def _at_item_updated(self, item):
        item_index = self._itemlist.index(item)
        index = self.index(item_index, 0)
        self.dataChanged.emit(index, index)


class ChatterItemFormatter:
    def __init__(self, avatars):
        self._avatars = avatars

    @classmethod
    def build(cls, avatar_dler, **kwargs):
        return cls(avatar_dler)

    def map_icon(self, data):
        name = data.map_name()
        return None if name is None else maps.preview(name)

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
        try:
            return data.player.league["league"]
        except (TypeError, AttributeError, KeyError):
            return "civilian"

    def chatter_avatar_icon(self, data):
        avatar_url = data.avatar_url()
        if avatar_url is None:
            return None
        if avatar_url not in self._avatars.avatars:
            return
        return QIcon(self._avatars.avatars[avatar_url])

    def chatter_country(self, data):
        if data.player is None:
            return '__'
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
        tooltip_str = formatting.format((int(player.rating_estimate())),
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

        game_str = formatting.format(header, game.title, game.featured_mod,
                                     game.mapdisplayname, game.num_players,
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
        return data.game.mapdisplayname

    def country_tooltip(self, data):
        return self.chatter_country(data)

    def nick_tooltip(self, data):
        return self.country_tooltip(data)


class ChatterContextMenu(QMenu):
    def __init__(self, parent_widget, chatter, player, game):
        QMenu.__init__(self, parent_widget)
        self.chatter = chatter
        self.player = player
        self.game = game
        self._init_entries()

    @classmethod
    def builder(cls, parent_widget, **kwargs):
        def make(data):
            return cls(parent_widget, data.chatter, data.player, data.game)
        return make

    # TODO - add mod entries
    # TODO - add entries for me
    # TODO - friend entries
    def _init_entries(self):
        if self.chatter is not None:
            self._init_chatter_entries()
        if self.player is not None:
            self.addSeparator()
            self._init_player_entries()
        if self.game is not None:
            self.addSeparator()
            self._init_game_entries()

    def _init_chatter_entries(self):
        self._add_menu("Dummy", lambda: None)

    def _init_player_entries(self):
        pass

    def _init_game_entries(self):
        pass

    def _add_menu(self, name, callback):
        action = QAction(name, self)
        action.triggered.connect(callback)
        self.addAction(action)


class ChatterItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, layout, formatter, context_menu_builder):
        QtWidgets.QStyledItemDelegate.__init__(self)
        self.layout = layout
        self._context_menu_builder = context_menu_builder
        self._formatter = formatter

    @classmethod
    def build(cls, **kwargs):
        layout = ChatterLayout.build(**kwargs)
        formatter = ChatterItemFormatter.build(**kwargs)
        context_menu_builder = ChatterContextMenu.builder(**kwargs)
        return cls(layout, formatter, context_menu_builder)

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

        self._draw_nick(painter, data)
        self._draw_status(painter, data)
        self._draw_map(painter, data)
        self._draw_rank(painter, data)
        self._draw_avatar(painter, data)
        self._draw_country(painter, data)

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
        text = data.chatter.name
        clip = QRectF(self.layout.sizes[ChatterLayoutElements.NICK])
        top_left = clip.topLeft()
        clip.moveTopLeft(QPoint(0, 0))

        painter.translate(top_left)
        html = QtGui.QTextDocument()
        html.setHtml(text)
        html.drawContents(painter, clip)
        painter.translate(top_left * -1)

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
        icon = util.THEME.icon("chat/countries/{}.png".format(country.lower()))
        self._draw_icon(painter, icon, ChatterLayoutElements.COUNTRY)

    def _draw_icon(self, painter, icon, element):
        rect = self.layout.sizes[element]
        icon.paint(painter, rect, QtCore.Qt.AlignCenter)

    def sizeHint(self, option, index):
        return self.layout.size

    def get_tooltip(self, index, pos):
        data = index.data()
        for elem in ChatterLayoutElements:
            if self.layout.sizes[elem].contains(pos):
                return self._tooltip(data, elem)
        return None

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

    def get_context_menu(self, index, pos):
        data = index.data()
        return self._context_menu_builder(data)


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

    def __init__(self, size, theme):
        QObject.__init__(self)
        self.theme = theme
        self._size = size
        self.sizes = {}
        self.load_layout()

    @classmethod
    def build(cls, chatter_size, theme, **kwargs):
        return cls(chatter_size, theme)

    def load_layout(self):
        formc, basec = self.theme.loadUiType(self.LAYOUT_FILE)
        self._form = formc()
        self._base = basec()
        self._form.setupUi(self._base)
        self._update_layout()

    @property
    def size(self):
        return self._base.size()

    @size.setter
    def size(self, size):
        self._size = size
        self._update_layout()

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
    def __init__(self, handler):
        QObject.__init__(self)
        self._handler = handler

    @classmethod
    def build(cls, handler, **kwargs):
        return cls(handler)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.ToolTip:
            return self._handle_tooltip(obj, event)
        elif event.type() == QtCore.QEvent.MouseButtonRelease:
            if event.button() == QtCore.Qt.RightButton:
                return self._handle_context_menu(obj, event)
        return super().eventFilter(obj, event)

    def _get_index_and_point(self, widget, event):
        view = widget.parent()
        idx = view.indexAt(event.pos())
        if not idx.isValid():
            return None, None
        item_rect = view.visualRect(idx)
        point = event.pos() - item_rect.topLeft()
        return idx, point

    def _handle_tooltip(self, widget, event):
        idx, point = self._get_index_and_point(widget, event)
        if idx is None:
            return False
        tooltip_text = self._handler.get_tooltip(idx, point)
        if tooltip_text is None:
            return False

        QtWidgets.QToolTip.showText(event.globalPos(), tooltip_text, widget)
        return True

    def _handle_context_menu(self, widget, event):
        idx, point = self._get_index_and_point(widget, event)
        if idx is None:
            return False

        menu = self._handler.get_context_menu(idx, point)
        menu.popup(QtGui.QCursor.pos())
        return True
