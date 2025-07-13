from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from enum import Enum
from typing import TYPE_CHECKING
from typing import Self

from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal

from src.model.modelitem import ModelItem
from src.model.transaction import transactional

if TYPE_CHECKING:
    from src.model.chat.chatline import ChatLineMetadata

PARTY_CHANNEL_SUFFIX = "'sParty"


class ChannelType(Enum):
    PUBLIC = 1
    PRIVATE = 2


class ChannelID:
    def __init__(self, type_: ChannelType, name: str) -> None:
        self.type = type_
        self.name = name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ChannelID):
            return NotImplemented
        return self.type == other.type and self.name == other.name

    def __hash__(self):
        return hash((self.name, self.type))

    @classmethod
    def private_cid(cls, name: str) -> Self:
        return cls(ChannelType.PRIVATE, name)


class Lines(QObject):
    added = pyqtSignal()
    removed = pyqtSignal(int)

    # FIXME: this is hacky, but was quick to implement
    _lines: dict[str, list[ChatLineMetadata]] = defaultdict(list)

    def __init__(self, channel_name: str) -> None:
        super().__init__()
        self.channel_name = channel_name

    def add_line(self, line: ChatLineMetadata) -> None:
        if line in self._lines[self.channel_name]:
            return
        self._lines[self.channel_name].append(line)
        self.added.emit()

    def remove_lines(self, number: int) -> None:
        number = min(number, len(self))
        if number < 0:
            raise ValueError
        if number == 0:
            return
        del self._lines[self.channel_name][0:number]
        self.removed.emit(number)

    def __getitem__(self, n: int) -> ChatLineMetadata:
        return self._lines[self.channel_name][n]

    def __iter__(self) -> Iterator[ChatLineMetadata]:
        return iter(self._lines[self.channel_name])

    def __len__(self) -> int:
        return len(self._lines[self.channel_name])

    def clear(self) -> None:
        self._lines[self.channel_name].clear()


class Channel(ModelItem):
    added_chatter = pyqtSignal(object)
    removed_chatter = pyqtSignal(object)

    def __init__(self, id_, lines, topic, is_base=False):
        ModelItem.__init__(self)
        self.add_field("topic", topic)
        self.add_field("is_base", is_base)
        self.lines = lines
        self.id = id_
        self.chatters = {}

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

    @transactional
    def add_chatter(self, cc, _transaction=None):
        self.chatters[cc.id_key] = cc
        _transaction.emit(self.added_chatter, cc)

    @transactional
    def remove_chatter(self, cc, _transaction=None):
        del self.chatters[cc.id_key]
        _transaction.emit(self.removed_chatter, cc)
