from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal
from model.modelitem import ModelItem
from model.transaction import transactional


class ChannelType(Enum):
    PUBLIC = 1
    PRIVATE = 2


class ChannelID:
    def __init__(self, type_, name):
        self.type = type_
        self.name = name

    def __eq__(self, other):
        return self.type == other.type and self.name == other.name

    def __hash__(self):
        return hash((self.name, self.type))


class Lines(QObject):
    added = pyqtSignal(int)
    removed = pyqtSignal(int)

    def __init__(self):
        QObject.__init__(self)
        self._lines = []

    def add_line(self, line):
        self._lines.append(line)
        self.added.emit(1)

    def remove_lines(self, number):
        number = min(number, len(self._lines))
        if number < 0:
            raise ValueError
        if number == 0:
            return

        del self._lines[0:number]
        self.removed.emit(number)

    def __getitem__(self, n):
        return self._lines[n]

    def __iter__(self):
        return iter(self._lines)

    def __len__(self):
        return len(self._lines)


class Channel(ModelItem):
    def __init__(self, id_, lines, topic):
        ModelItem.__init__(self)
        self.add_field("topic", topic)
        self.lines = lines
        self.id = id_

    @property
    def id_key(self):
        return self.id

    def copy(self):
        return Channel(self.id, self.lines, **self.field_dict)

    @transactional
    def update(self, **kwargs):
        _transaction = kwargs.pop("_transaction")

        old = self.copy()
        ModelItem.update(self, **kwargs)
        self.emit_update(old, _transaction)

    @transactional
    def set_topic(self, topic, _transaction=None):
        self.update(topic=topic, _transaction=_transaction)
