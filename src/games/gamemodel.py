from PyQt5.QtCore import Qt, QSortFilterProxyModel
from .gamemodelitem import GameModelItem
from enum import Enum

from games.moditem import mod_invisible
from model.game import GameState
from util.qt_list_model import QtListModel


class GameModel(QtListModel):
    def __init__(self, me, preview_dler, gameset=None):
        builder = GameModelItem.builder(me, preview_dler)
        QtListModel.__init__(self, builder)

        self._gameset = gameset
        if self._gameset is not None:
            self._gameset.added.connect(self.add_game)
            self._gameset.newClosedGame.connect(self.remove_game)
            for game in self._gameset.values():
                self.add_game(game)

    def add_game(self, game):
        self._add_item(game, game.uid)

    def remove_game(self, game):
        self._remove_item(game.uid)

    def clear_games(self):
        self._clear_items()


class GameSortModel(QSortFilterProxyModel):
    class SortType(Enum):
        PLAYER_NUMBER = 0
        AVERAGE_RATING = 1
        MAPNAME = 2
        HOSTNAME = 3
        AGE = 4

    def __init__(self, me, model):
        QSortFilterProxyModel.__init__(self)
        self._sort_type = self.SortType.AGE
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
        return (self._me.relations.model.is_friend(hostl) and
                not self._me.relations.model.is_friend(hostr))

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

        return self.filter_accepts_game(game)

    def filter_accepts_game(self, game):
        return True


class CustomGameFilterModel(GameSortModel):
    def __init__(self, me, model):
        GameSortModel.__init__(self, me, model)
        self._hide_private_games = False

    def filter_accepts_game(self, game):
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
