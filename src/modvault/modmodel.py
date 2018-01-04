from PyQt5.QtCore import QAbstractListModel, Qt, QSortFilterProxyModel, QModelIndex
from .modmodelitem import ModModelItem
from enum import Enum


class ModModel(QAbstractListModel):
    def __init__(self, me, modset=None):
        QAbstractListModel.__init__(self)
        self._me = me
        self._moditems = {}
        self._itemlist = []  # For queries

        self._modset = modset
        if self._modset is not None:
            self._modset.newMod.connect(self.add_mod)
            self._modset.removedMod.connect(self.remove_mod)

            for mod in self._modset.values():
                self.add_mod(mod)

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

    def add_mod(self, mod):
        assert mod.uid not in self._moditems

        next_index = len(self._itemlist)
        self.beginInsertRows(QModelIndex(), next_index, next_index)

        item = ModModelItem(mod, self._me)
        item.mmI_updated.connect(self._at_item_updated)

        self._moditems[mod.uid] = item
        self._itemlist.append(item)

        self.endInsertRows()

    def remove_mod(self, mod):
        assert mod.uid in self._moditems

        item = self._moditems[mod.uid]
        item_index = self._itemlist.index(item)
        self.beginRemoveRows(QModelIndex(), item_index, item_index)

        item.mmI_updated.disconnect(self._at_item_updated)
        del self._moditems[mod.uid]
        self._itemlist.pop(item_index)
        self.endRemoveRows()

    def _at_item_updated(self, item):
        item_index = self._itemlist.index(item)
        index = self.index(item_index, 0)
        self.dataChanged.emit(index, index)


class ModSortModel(QSortFilterProxyModel):
    class SortType(Enum):
        ALPHABETICAL = 0
        DATE = 1
        RATING = 2
        DOWNLOADS = 3

    def __init__(self, model):
        QSortFilterProxyModel.__init__(self)
        self._sort_type = self.SortType.RATING
        self.setSourceModel(model)
        self.sort(0)

    def lessThan(self, left_index, right_index):
        left = self.sourceModel().data(left_index, Qt.DisplayRole).mod
        right = self.sourceModel().data(right_index, Qt.DisplayRole).mod

        comp_list = [self._lt_type, self._lt_fallback]

        for lt in comp_list:
            if lt(left, right):
                return True
            elif lt(right, left):
                return False
        return False

    def _lt_type(self, left, right):
        stype = self._sort_type
        stypes = self.SortType

        if stype == stypes.ALPHABETICAL:
            if left.name.lower() == right.name.lower():
                return left.version > right.version
            return left.name.lower() < right.name.lower()
        elif stype == stypes.DATE:
            if left.date == right.date:
                return left.name.lower() < right.name.lower()
            return left.date > right.date
        elif stype == stypes.RATING:
            if left.likes == right.likes:
                return left.date > right.date
            return left.likes > right.likes
        elif stype == stypes.DOWNLOADS:
            if left.downloads == right.downloads:
                return left.date > right.date
            return left.downloads > right.downloads

    @staticmethod
    def _lt_fallback(left, right):
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
        mod = index.data().mod

        return self.filter_accepts_mod(mod)

    def filter_accepts_mod(self, mod):
        return True


class ModFilterModel(ModSortModel):
    class FilterType(Enum):
        ALL = 0
        UI = 1
        SIM = 2
        YOURS = 3
        INSTALLED = 4

    def __init__(self, model):
        self._filter_type = self.FilterType.ALL
        self._search_str = ""
        ModSortModel.__init__(self, model)

    def filter_accepts_mod(self, mod):
        search_str = self._search_str
        if search_str != "":
            if not (mod.author.lower().find(search_str) != -1 or mod.name.lower().find(search_str) != -1 or
                    mod.description.lower().find(search_str) != -1):
                return False
        ftype = self._filter_type
        ftypes = self.FilterType
        if ftype == ftypes.ALL:
            return True
        elif ftype == ftypes.UI:
            return mod.is_uimod
        elif ftype == ftypes.SIM:
            return not mod.is_uimod
        elif ftype == ftypes.YOURS:
            return mod.uploaded_byuser
        elif ftype == ftypes.INSTALLED:
            return mod.installed

        return True

    @property
    def filter_type(self):
        return self._filter_type

    @filter_type.setter
    def filter_type(self, ftype):
        self._filter_type = ftype
        self.invalidateFilter()

    @property
    def search_str(self):
        return self._search_str

    @search_str.setter
    def search_str(self, sstr):
        self._search_str = sstr
        self.invalidateFilter()
