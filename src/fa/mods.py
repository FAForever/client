import logging

from PyQt5 import QtWidgets

import config
import fa
import vaults.modvault.utils

logger = logging.getLogger(__name__)


def checkMods(mods):  # mods is a dictionary of uid-name pairs
    """
    Assures that the specified mods are available in FA, or returns False.
    Also sets the correct active mods in the ingame mod manager.
    """
    logger.info("Updating FA for mods {}".format(", ".join(mods)))
    to_download = []
    inst = vaults.modvault.utils.getInstalledMods()
    uids = [mod.uid for mod in inst]
    for uid in mods:
        if uid not in uids:
            to_download.append(uid)

    auto = config.Settings.get('mods/autodownload', default=False, type=bool)
    if not auto:
        mod_names = ", ".join([mods[uid] for uid in mods])
        msgbox = QtWidgets.QMessageBox()
        msgbox.setWindowTitle("Download Mod")
        msgbox.setText(
            "Seems that you don't have mods used in this game. Do "
            "you want to download them?<br/><b>{}</b>".format(mod_names),
        )
        msgbox.setInformativeText(
            "If you respond 'Yes to All' mods will be "
            "downloaded automatically in the future",
        )
        msgbox.setStandardButtons(
            QtWidgets.QMessageBox.Yes
            | QtWidgets.QMessageBox.YesToAll
            | QtWidgets.QMessageBox.No,
        )
        result = msgbox.exec_()
        if result == QtWidgets.QMessageBox.No:
            return False
        elif result == QtWidgets.QMessageBox.YesToAll:
            config.Settings.set('mods/autodownload', True)

    for uid in to_download:
        # Spawn an update for the required mod
        updater = fa.updater.Updater(uid, sim=True)
        result = updater.run()
        if result != fa.updater.Updater.RESULT_SUCCESS:
            logger.warning("Failure getting {}: {}".format(uid, mods[uid]))
            return False

    actual_mods = []
    inst = vaults.modvault.utils.getInstalledMods()
    uids = {}
    for mod in inst:
        uids[mod.uid] = mod
    for uid in mods:
        if uid not in uids:
            QtWidgets.QMessageBox.warning(
                None,
                "Mod not Found",
                (
                    "{} was apparently not installed correctly. Please check "
                    "this.".format(mods[uid])
                ),
            )
            return
        actual_mods.append(uids[uid])
    if not vaults.modvault.utils.setActiveMods(actual_mods):
        logger.warning("Couldn't set the active mods in the game.prefs file")
        return False

    return True
