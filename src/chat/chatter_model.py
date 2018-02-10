from PyQt5.QtCore import QObject, pyqtSignal, QAbstractListModel, Qt, \
        QModelIndex
from PyQt5 import QtWidgets, QtCore, QtGui


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
    def __init__(self):
        QtWidgets.QStyledItemDelegate.__init__(self)

    def paint(self, painter, option, index):
        painter.save()

        data = index.data()
        text = self._get_text(data)

        self._draw_clear_option(painter, option)
        self._handle_highlight(painter, option)

        painter.translate(option.rect.left(), option.rect.top())
        self._draw_text(painter, option, text)

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

    def _draw_text(self, painter, option, text):
        clip = QtCore.QRectF(0,
                             0,
                             100,
                             20)
        html = QtGui.QTextDocument()
        html.setHtml(text)
        html.drawContents(painter, clip)

    def sizeHint(self, option, index):
        return QtCore.QSize(100, 20)
