from enum import Enum
from PyQt5.QtCore import QObject, QAbstractListModel, Qt, QModelIndex, \
    QRectF, QPoint
from PyQt5 import QtWidgets, QtGui, QtCore
from chat.chatter_model_item import ChatterModelItem
import util


class ChatterModel(QAbstractListModel):
    def __init__(self, channel, map_preview_dler, avatar_dler):
        QAbstractListModel.__init__(self)
        self._channel = channel
        self._itemlist = []
        self._items = {}
        self._map_preview_dler = map_preview_dler
        self._avatar_dler = avatar_dler

        if self._channel is not None:
            self._channel.added_chatter.connect(self.add_chatter)
            self._channel.removed_chatter.connect(self.remove_chatter)

        for chatter in self._channel.chatters:
            self.add_chatter(chatter)

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

        item = ChatterModelItem(chatter, self._map_preview_dler,
                                self._avatar_dler)
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


class ChatterItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, layout, parent):
        QtWidgets.QStyledItemDelegate.__init__(self)
        self.layout = layout
        self._parent = parent
        self.tooltip = ChatterEventFilter(self)

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
        status = data.chatter_status()
        icon = util.THEME.icon("chat/status/{}.png".format(status))
        self._draw_icon(painter, icon, ChatterLayoutElements.STATUS)

    # TODO - handle optionality of maps
    def _draw_map(self, painter, data):
        icon = data.map_icon()
        if not icon:
            return
        self._draw_icon(painter, icon, ChatterLayoutElements.MAP)

    def _draw_rank(self, painter, data):
        rank = data.chatter_rank()
        icon = util.THEME.icon("chat/rank/{}.png".format(rank))
        self._draw_icon(painter, icon, ChatterLayoutElements.RANK)

    def _draw_avatar(self, painter, data):
        icon = data.chatter_avatar_icon()
        if not icon:
            return
        self._draw_icon(painter, icon, ChatterLayoutElements.AVATAR)

    def _draw_country(self, painter, data):
        country = data.chatter_country()
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
            return data.rank_tooltip()
        elif item == ChatterLayoutElements.STATUS:
            return data.status_tooltip()
        elif item == ChatterLayoutElements.AVATAR:
            return data.avatar_tooltip()
        elif item == ChatterLayoutElements.MAP:
            return data.map_tooltip()
        elif item == ChatterLayoutElements.COUNTRY:
            return data.country_tooltip()
        elif item == ChatterLayoutElements.NICK:
            return data.nick_tooltip()

    def get_context_menu(self, index, pos):
        data = index.data()
        return data.context_menu(self._parent)


class ChatterLayoutElements(Enum):
    RANK = "rankBox"
    STATUS = "statusBox"
    AVATAR = "avatarBox"
    MAP = "mapBox"
    COUNTRY = "countryBox"
    NICK = "nickBox"


class ChatterLayout(QObject):
    """Provides layout info for delegate using Qt widget layouts."""

    def __init__(self, theme, layout_file, size):
        QObject.__init__(self)
        self.theme = theme
        self._size = size
        self.sizes = {}
        self.layout = layout_file

    @property
    def layout(self):
        return self._layout

    @layout.setter
    def layout(self, layout):
        self._layout = layout
        formc, basec = self.theme.loadUiType(layout)
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


def build_delegate(size, parent):
    layout = ChatterLayout(util.THEME, "chat/chatter.ui", size)
    return ChatterItemDelegate(layout, parent)


class ChatterEventFilter(QObject):
    def __init__(self, handler):
        QObject.__init__(self)
        self._handler = handler

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
