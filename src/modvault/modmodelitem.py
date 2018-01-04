from PyQt5.QtCore import QObject, pyqtSignal
from modvault.utils import getIcon, installedMods
import urllib.parse
import os
import util


class ModModelItem(QObject):
    """
    UI representation of a mod.
    """
    mmI_updated = pyqtSignal(object)

    def __init__(self, mod, me):
        QObject.__init__(self)

        self.mod = mod
        self.mod.modUpdated.connect(self._mod_updated)
        self._me = me
        self._uids = [mod.uid for mod in installedMods]
        if mod.thumbnail == "":
            self.mod_icon = util.THEME.icon("games/unknown_map.png")
        else:
            name = os.path.basename(urllib.parse.unquote(mod.thumbnail))
            img = getIcon(name)
            if img:  # in cache
                self.mod_icon = util.THEME.icon(img, False)
            else:  # should be downloaded
                self.mod_icon = util.THEME.icon("games/private_game.png")
        mod.thumbnail = self.mod_icon
        mod.installed = mod.uid in self._uids
        mod.uploaded_byuser = (mod.author == self._me.login)

    def _mod_updated(self):
        self.mmI_updated.emit(self)
