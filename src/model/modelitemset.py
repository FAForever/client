from PyQt5.QtCore import pyqtSignal
from model.qobjectmapping import QObjectMapping
from model.transaction import transactional


class ModelItemSet(QObjectMapping):
    added = pyqtSignal(object)
    removed = pyqtSignal(object)
    before_added = pyqtSignal(object, object)
    before_removed = pyqtSignal(object, object)

    def __init__(self):
        QObjectMapping.__init__(self)

        self._items = {}

    def __getitem__(self, item):
        return self._items[item]

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def emit_added(self, value, _transaction=None):
        _transaction.emit(self.added, value)
        self.before_added.emit(value, _transaction)

    def emit_removed(self, value, _transaction=None):
        _transaction.emit(self.removed, value)
        self.before_removed.emit(value, _transaction)

    @transactional
    def set_item(self, key, value, _transaction=None):
        if key in self:
            raise ValueError
        if key != value.id_key:
            raise ValueError
        self._items[key] = value

    def __setitem__(self, key, value):
        # CAVEAT: use only as an entry point for model changes.
        self.set_item(key, value)

    @transactional
    def del_item(self, item, _transaction=None):
        try:
            value = self[item]
        except KeyError:
            return None
        del self._items[value.id_key]
        return value

    def __delitem__(self, item):
        # CAVEAT: use only as an entry point for model changes.
        self.del_item(item)

    @transactional
    def clear(self, _transaction=None):
        items = list(self.keys())
        for item in items:
            self.del_item(item, _transaction)
