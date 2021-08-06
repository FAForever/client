from PyQt5.QtCore import pyqtSignal

from model.qobjectmapping import QObject
from model.transaction import transactional


class ModelItem(QObject):
    updated = pyqtSignal(object, object)
    before_updated = pyqtSignal(object, object, object)

    def __init__(self):
        QObject.__init__(self)
        self._data_fields = []

    def add_field(self, name, default):
        self._data_fields.append(name)
        setattr(self, name, default)

    @property
    def field_dict(self):
        return {v: getattr(self, v) for v in self._data_fields}

    def copy(self):
        raise NotImplementedError

    def update(self, **kwargs):
        # Ignore unknown fields for convenience
        for f in self._data_fields:
            if f in kwargs:
                setattr(self, f, kwargs[f])

    @transactional
    def emit_update(self, old, _transaction=None):
        _transaction.emit(self.updated, self, old)
        self.before_updated.emit(self, old, _transaction)

    @property
    def id_key(self):
        raise NotImplementedError

    def __hash__(self):
        return hash(self.id_key)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.id_key == other.id_key
