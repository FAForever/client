from PyQt5.QtCore import QObject, pyqtSignal, QAbstractListModel, Qt, \
        QModelIndex, QRectF, QPoint
from PyQt5 import QtWidgets, QtGui, QtCore
from enum import Enum
import util


class ChatterModelItem(QObject):
    """
    UI representation of a chatter.
    """
    updated = pyqtSignal(object)

    def __init__(self, cc):
        QObject.__init__(self)
        self.cc = cc
        self.cc.chatter.updated.connect(self._chatter_updated)

    def _chatter_updated(self):
        self.updated.emit(self)


class ChatterModel(QAbstractListModel):
    def __init__(self, channel):
        QAbstractListModel.__init__(self)
        self._channel = channel
        self._itemlist = []
        self._items = {}

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

        item = ChatterModelItem(chatter)
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
    def __init__(self, layout):
        QtWidgets.QStyledItemDelegate.__init__(self)
        self.layout = layout

    def update_width(self, size):
        current_size = self.layout.size
        if size.width() != current_size.width():
            current_size.setWidth(size.width())
            self.layout.size = current_size

    def paint(self, painter, option, index):
        painter.save()

        data = index.data()
        text = self._get_text(data)

        self._draw_clear_option(painter, option)
        self._handle_highlight(painter, option)

        painter.translate(option.rect.left(), option.rect.top())

        self._draw_nick(painter, text)
        self._draw_status(painter)
        self._draw_map(painter)
        self._draw_rank(painter)
        self._draw_avatar(painter)

        painter.restore()

    def _get_text(self, data):
        return data.cc.chatter.name

    def _draw_clear_option(self, painter, option):
        option.icon = QtGui.QIcon()
        option.text = ""
        option.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem,
                                          option, painter, option.widget)

    def _handle_highlight(self, painter, option):
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight)

    def _draw_nick(self, painter, text):
        clip = QRectF(self.layout.sizes[ChatterLayoutElements.NICK])
        top_left = clip.topLeft()
        clip.moveTopLeft(QPoint(0, 0))

        painter.translate(top_left)
        html = QtGui.QTextDocument()
        html.setHtml(text)
        html.drawContents(painter, clip)
        painter.translate(top_left * -1)

    def _draw_status(self, painter):
        icon = util.THEME.icon("chat/status/playing.png")
        rect = self.layout.sizes[ChatterLayoutElements.STATUS]
        icon.paint(painter, rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

    def _draw_map(self, painter):
        icon = util.THEME.icon("chat/status/playing.png")
        rect = self.layout.sizes[ChatterLayoutElements.MAP]
        icon.paint(painter, rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

    def _draw_rank(self, painter):
        icon = util.THEME.icon("chat/status/playing.png")
        rect = self.layout.sizes[ChatterLayoutElements.RANK]
        icon.paint(painter, rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

    def _draw_avatar(self, painter):
        icon = util.THEME.icon("chat/status/playing.png")
        rect = self.layout.sizes[ChatterLayoutElements.AVATAR]
        icon.paint(painter, rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

    def sizeHint(self, option, index):
        return self.layout.size


class ChatterLayoutElements(Enum):
    RANK = "rankBox"
    STATUS = "statusBox"
    AVATAR = "avatarBox"
    MAP = "mapBox"
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


def build_delegate(size):
    layout = ChatterLayout(util.THEME, "chat/chatter.ui", size)
    return ChatterItemDelegate(layout)
