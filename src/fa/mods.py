from PyQt4 import QtGui
import fa
import modvault


__author__ = 'Thygrrr'

import logging
logger = logging.getLogger(__name__)

def checkMods(mods):  #mods is a dictionary of uid-name pairs
    """
    Assures that the specified mods are available in FA, or returns False.
    Also sets the correct active mods in the ingame mod manager.
    """
    logger.info("Updating FA for mods %s" % ", ".join(mods))
    to_download = []
    inst = modvault.getInstalledMods()
    uids = [mod.uid for mod in inst]
    for uid in mods:
        if uid not in uids:
            to_download.append(uid)

    for uid in to_download:
        result = QtGui.QMessageBox.question(None, "Download Mod",
                                            "Seems that you don't have this mod. Do you want to download it?<br/><b>" +
                                            mods[uid] + "</b>", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if result == QtGui.QMessageBox.Yes:
            # Spawn an update for the required mod
            updater = fa.updater.Updater(uid, sim=True)
            result = updater.run()
            updater = None  #Our work here is done
            if (result != fa.updater.Updater.RESULT_SUCCESS):
                return False
        else:
            return False

    actual_mods = []
    inst = modvault.getInstalledMods()
    uids = {}
    for mod in inst:
        uids[mod.uid] = mod
    for uid in mods:
        if uid not in uids:
            QtGui.QMessageBox.warning(None, "Mod not Found",
                                      "%s was apparently not installed correctly. Please check this." % mods[uid])
            return
        actual_mods.append(uids[uid])
    if not modvault.setActiveMods(actual_mods):
        logger.warn("Couldn't set the active mods in the game.prefs file")
        return False

    return True