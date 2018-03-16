from PyQt5.QtCore import QObject
from collections.abc import KeysView, ItemsView, ValuesView


class QObjectMapping(QObject):
    """
    ABC similar to collections.abc.MutableMapping.
    Used since we can't mixin the above with QObject.
    """

    def __init__(self):
        QObject.__init__(self)

    def __len__(self):
        return 0

    def __iter__(self):
        while False:
            yield None

    def __getitem__(self, key):
        raise KeyError

    def __setitem__(self, key, value):
        raise KeyError

    def __delitem__(self, key):
        raise KeyError

    __marker = object()

    def pop(self, key, default=__marker):
        try:
            value = self[key]
        except KeyError:
            if default is self.__marker:
                raise
            return default
        else:
            del self[key]
            return value

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    def keys(self):
        return KeysView(self)

    def values(self):
        return ValuesView(self)

    def items(self):
        return ItemsView(self)
