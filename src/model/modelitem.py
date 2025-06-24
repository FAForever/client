from typing import Any

from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal

from src.model.transaction import transactional


class ModelItem(QObject):
    updated = pyqtSignal(object, object)
    before_updated = pyqtSignal(object, object, object)

    def __init__(self):
        QObject.__init__(self)
        self._data_fields: list[str] = []

    def add_field(self, name: str, default: Any) -> None:
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
        if not isinstance(self, type(other)):
            return False
        return self.id_key == other.id_key
