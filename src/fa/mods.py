import logging

from PyQt6 import QtWidgets

from src import config
from src.api.sim_mod_updater import SimModFiles
from src.vaults.modvault.utils import downloadMod
from src.vaults.modvault.utils import getInstalledMods
from src.vaults.modvault.utils import setActiveMods

logger = logging.getLogger(__name__)


def checkMods(mods: dict[str, str]) -> bool:  # mods is a dictionary of uid-name pairs
    """
    Assures that the specified mods are available in FA, or returns False.
    Also sets the correct active mods in the ingame mod manager.
    """
    logger.info("Updating FA for mods %s", ", ".join(mods))

    inst = set(mod.uid for mod in getInstalledMods())
    to_download = {uid: name for uid, name in mods.items() if uid not in inst}

    auto = config.Settings.get('mods/autodownload', default=False, type=bool)
    if not auto:
        mod_names = ", ".join(mods.values())
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
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.YesToAll
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        result = msgbox.exec()
        if result == QtWidgets.QMessageBox.StandardButton.No:
            return False
        elif result == QtWidgets.QMessageBox.StandardButton.YesToAll:
            config.Settings.set('mods/autodownload', True)

    api_accessor = SimModFiles()
    for uid, name in to_download.items():
        url = api_accessor.request_and_get_sim_mod_url_by_id(uid)
        if not downloadMod(url, name):
            logger.warning("Failure getting '%s' with uid '%s'", name, uid)
            return False

    actual_mods = []
    uids = {mod.uid: mod for mod in getInstalledMods()}
    for uid, name in mods.items():
        if uid not in uids:
            QtWidgets.QMessageBox.warning(
                None,
                "Mod not Found",
                f"{name} was apparently not installed correctly. Please check this.",
            )
            return
        actual_mods.append(uids[uid])
    if not setActiveMods(actual_mods):
        logger.warning("Couldn't set the active mods in the game.prefs file")
        return False

    return True
