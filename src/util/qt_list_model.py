from PyQt5.QtCore import QAbstractListModel, QModelIndex, Qt


class QtListModel(QAbstractListModel):
    def __init__(self, item_builder):
        QAbstractListModel.__init__(self)
        self._items = {}
        self._itemlist = []  # For queries
        self._item_builder = item_builder

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self._itemlist)

    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self._itemlist):
            return None
        if role != Qt.DisplayRole:
            return None
        return self._itemlist[index.row()]

    # TODO - insertion and removal are O(n).
    def _add_item(self, data, id_):
        assert id_ not in self._items
        next_index = len(self._itemlist)
        self.beginInsertRows(QModelIndex(), next_index, next_index)
        item = self._item_builder(data)
        item.updated.connect(self._at_item_updated)
        self._items[id_] = item
        self._itemlist.append(item)
        self.endInsertRows()

    def _remove_item(self, id_):
        assert id_ in self._items
        item = self._items[id_]
        item_index = self._itemlist.index(item)
        self.beginRemoveRows(QModelIndex(), item_index, item_index)
        item.updated.disconnect(self._at_item_updated)
        del self._items[id_]
        self._itemlist.pop(item_index)
        self.endRemoveRows()

    def _clear_items(self):
        self.beginRemoveRows(QModelIndex(), 0, len(self._items) - 1)
        for item in self._items.values():
            item.updated.disconnect(self._at_item_updated)
        self._items.clear()
        self._itemlist.clear()
        self.endRemoveRows()

    def _at_item_updated(self, item):
        item_index = self._itemlist.index(item)
        index = self.index(item_index, 0)
        self.dataChanged.emit(index, index)
