from PyQt5.QtCore import QAbstractListModel, Qt
from PyQt5.QtCore import QModelIndex
from .gamemodelitem import GameModelItem


class GameModel(QAbstractListModel):
    def __init__(self, gameset, me):
        QAbstractListModel.__init__(self)
        self._me = me

        self._gameitems = {}

        # For queries
        self._itemlist = []

        self._gameset = gameset
        self._gameset.newGame.connect(self._addGame)
        self._gameset.newClosedGame.connect(self._removeGame)

        for game in self._gameset.values():
            self._addGame(game)

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

    # TODO - insertion and removal are O(n). Server bandwidth would probably
    # become a bigger issue if number of games increased too much though.

    def _addGame(self, game):
        assert game.uid not in self._gameitems

        next_index = len(self._itemlist)
        self.beginInsertRows(QModelIndex(), next_index, next_index)

        item = GameModelItem(game, self._me)
        item.updated.connect(self._at_item_updated)

        self._gameitems[game.uid] = item
        self._itemlist.append(item)

        self.endInsertRows()

    def _removeGame(self, game):
        assert game.uid in self._gameitems

        item = self._gameitems[game.uid]
        item_index = self._itemlist.index(item)
        self.beginRemoveRows(QModelIndex(), item_index, item_index)

        item.updated.disconnect(self._at_item_updated)
        del self._gameitems[game.uid]
        self._itemlist.pop(item_index)
        self.endRemoveRows()

    def _at_item_updated(self, item):
        item_index = self._itemlist.index(item)
        index = self.index(item_index, 0)
        self.dataChanged.emit(index, index)
