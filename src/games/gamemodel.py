from PyQt5.QtCore import QAbstractListModel, Qt, QSortFilterProxyModel
from PyQt5.QtCore import QModelIndex
from .gamemodelitem import GameModelItem
from enum import Enum

from games.moditem import mod_invisible
from model.game import GameState


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


class CustomGameFilterModel(QSortFilterProxyModel):
    class SortType(Enum):
        PLAYER_NUMBER = 0
        AVERAGE_RATING = 1
        MAPNAME = 2
        HOSTNAME = 3
        AGE = 4

    def __init__(self, me, model):
        QSortFilterProxyModel.__init__(self)
        self._sort_type = self.SortType.AGE
        self._hide_private_games = False
        self._me = me
        self.setSourceModel(model)
        self.sort(0)

    def lessThan(self, leftIndex, rightIndex):
        left = self.sourceModel().data(leftIndex, Qt.DisplayRole).game
        right = self.sourceModel().data(rightIndex, Qt.DisplayRole).game

        comp_list = [self._lt_friend, self._lt_type, self._lt_fallback]

        for lt in comp_list:
            if lt(left, right):
                return True
            elif lt(right, left):
                return False
        return False

    def _lt_friend(self, left, right):
        hostl = -1 if left.host_player is None else left.host_player.id
        hostr = -1 if right.host_player is None else right.host_player.id
        return self._me.isFriend(hostl) and not self._me.isFriend(hostr)

    def _lt_type(self, left, right):
        stype = self._sort_type
        stypes = self.SortType

        if stype == stypes.PLAYER_NUMBER:
            return len(left.players) > len(right.players)
        elif stype == stypes.AVERAGE_RATING:
            return left.average_rating > right.average_rating
        elif stype == stypes.MAPNAME:
            return left.mapdisplayname.lower() < right.mapdisplayname.lower()
        elif stype == stypes.HOSTNAME:
            return left.host.lower() < right.host.lower()
        elif stype == stypes.AGE:
            return left.uid < right.uid

    def _lt_fallback(self, left, right):
        return left.uid < right.uid

    @property
    def sort_type(self):
        return self._sort_type

    @sort_type.setter
    def sort_type(self, stype):
        self._sort_type = stype
        self.invalidate()

    def filterAcceptsRow(self, row, parent):
        index = self.sourceModel().index(row, 0, parent)
        if not index.isValid():
            return False
        game = index.data().game

        if game.state != GameState.OPEN:
            return False
        if game.featured_mod in mod_invisible:
            return False
        if self.hide_private_games and game.password_protected:
            return False

        return True

    @property
    def hide_private_games(self):
        return self._hide_private_games

    @hide_private_games.setter
    def hide_private_games(self, priv):
        self._hide_private_games = priv
        self.invalidateFilter()
