from PyQt4 import QtGui
import fa
import modvault
import logging
import config

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

    auto = config.Settings.get('mods/autodownload', default=False, type=bool)
    if not auto:
        mod_names = ", ".join([mods[uid] for uid in mods])
        msgbox = QtGui.QMessageBox()
        msgbox.setWindowTitle("Download Mod")
        msgbox.setText("Seems that you don't have mods used in this game. Do you want to download them?<br/><b>" + mod_names + "</b>")
        msgbox.setInformativeText("If you respond 'Yes to All' mods will be downloaded automatically in the future")
        msgbox.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.YesToAll | QtGui.QMessageBox.No)
        result = msgbox.exec_()
        if result == QtGui.QMessageBox.No:
            return False
        elif result == QtGui.QMessageBox.YesToAll:
            config.Settings.set('mods/autodownload', True)

    for uid in to_download:
        # Spawn an update for the required mod
        updater = fa.updater.Updater(uid, sim=True)
        result = updater.run()
        if result != fa.updater.Updater.RESULT_SUCCESS:
            logger.warning("Failure getting {}: {}".format(uid, mods[uid]))
            return False
        else:
            return True

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
