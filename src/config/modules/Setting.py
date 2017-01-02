import os
from PyQt4.QtCore import QObject, pyqtSignal, QDir
from config import Settings

class Setting(QObject):
    """
    Represents a global setting. Essentially does what Settings does, but
    allows to omit providing type and emits a signal when set.
    """
    changed = pyqtSignal()

    def __init__(self, name, _type = str):
        QObject.__init__(self)
        self._name = name
        self._type = _type

    def set(self, value, persist=True):
        Settings.set(self.name, value, persist)
        self.changed.emit()

    def get(self, default=None):
        return Settings.get(self.name, default, self._type)

    @property
    def name(self):
        return self._name

    def delete(self):
        return Settings.remove(self.name)

    def isSet(self):
        return Settings.contains(self.name)

class PathSetting(Setting):
    """
    Represents a setting that stores a path. Converts path on the fly between
    system and qt format.
    """
    def __init__(self, name):
        Setting.__init__(self,name,str)

    def set(self, value, persist=True):
        Setting.set(self,QDir.toNativeSeparators(value), persist)

    def get(self, default=None):
        # We store default ourselves to avoid conversion
        got = Setting.get(self,None)
        if got is None:
            # No setting should actually *set* it to None
            return default
        else:
            return QDir.fromNativeSeparators(got)

class PrefixedPathSetting(PathSetting):
    """
    Represents a relative path that needs to be prefixed to be useful.
    Prefix is set up at runtime. Note that you should NOT add the prefix
    if you want to change the relative path.
    """
    def __init__(self, name, prefix):
        self._prefix = prefix
        PathSetting.__init__(self,name)

    def get(self, default=None):
        got = PathSetting.get(self, default)
        return os.path.join(self._prefix, got) if got is not None else None
