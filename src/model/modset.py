from PyQt5.QtCore import QObject, pyqtSignal
from decorators import with_logger

from model import mod


@with_logger
class Modset(QObject):

    newMod = pyqtSignal(object)
    removedMod = pyqtSignal(object)

    def __init__(self):
        QObject.__init__(self)
        self.mods = {}

    def __getitem__(self, uid):
        return self.mods[uid]

    def __contains__(self, uid):
        return uid in self.mods

    def __iter__(self):
        return iter(self.mods)

    def keys(self):
        return self.mods.keys()

    def values(self):
        return self.mods.values()

    def items(self):
        return self.mods.items()

    def get(self, item, default=None):
        try:
            return self[item]
        except KeyError:
            return default

    def __setitem__(self, key, value):
        if not isinstance(key, str) or not isinstance(value, mod.Mod):
            raise TypeError

        if key in self:
            raise ValueError

        if key != value.uid:
            raise ValueError

        self.mods[key] = value
        # We should be the first ones to connect to the signal
        value.modUpdated.connect(self._at_mod_update)
        self._at_mod_update(value, None)
        self.newMod.emit(value)
        self._logger.debug("Added mod, uid {}".format(value.uid))

    def clear(self):
        # Abort_mod removes g from dict, so 'for g in values()' complains
        for g in list(self.mods.values()):
            g.abort_mod()

    def _at_mod_update(self, new, old):
        return

    def _remove_mod(self, mod):
        try:
            mod = self.mods[mod.uid]
            mod.modUpdated.disconnect(self._at_mod_update)
            del self.mods[mod.uid]
            self._logger.debug("Removed mod, uid {}".format(mod.uid))
        except KeyError:
            pass
