import logging

from PyQt4 import QtGui

import fa
import config
from fa.mods import checkMods
from fa.path import writeFAPathLua, validatePath
from fa.wizards import Wizard
import util

logger = logging.getLogger(__name__)


def map(mapname, force=False, silent=False):
    """
    Assures that the map is available in FA, or returns false.
    """
    logger.info("Updating FA for map: " + str(mapname))

    if fa.maps.isMapAvailable(mapname):
        logger.info("Map is available.")
        return True

    if force:
        return fa.maps.downloadMap(mapname, silent=silent)

    auto = config.Settings.get('maps/autodownload', default=False, type=bool)
    if not auto:
        msgbox = QtGui.QMessageBox()
        msgbox.setWindowTitle("Download Mod")
        msgbox.setText("Seems that you don't have the map used this game. Do you want to download it?<br/><b>" + mapname + "</b>")
        msgbox.setInformativeText("If you respond 'Yes to All' maps will be downloaded automatically in the future")
        msgbox.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.YesToAll | QtGui.QMessageBox.No)
        result = msgbox.exec_()
        if result == QtGui.QMessageBox.No:
            return False
        elif result == QtGui.QMessageBox.YesToAll:
            config.Settings.set('maps/autodownload', True)

    return fa.maps.downloadMap(mapname, silent=silent)

def featured_mod(featured_mod, version):
    pass


def sim_mod(sim_mod, version):
    pass


def path(parent):
    while not validatePath(util.settings.value("ForgedAlliance/app/path", "", type=str)):
        logger.warn("Invalid game path: " + util.settings.value("ForgedAlliance/app/path", "", type=str))
        wizard = Wizard(parent)
        result = wizard.exec_()
        if result == QtGui.QWizard.Rejected:
            return False

    logger.info("Writing fa_path.lua config file.")
    writeFAPathLua()


def game(parent):
    return True


def check(featured_mod, mapname=None, version=None, modVersions=None, sim_mods=None, silent=False):
    """
    This checks whether the mods are properly updated and player has the correct map.
    """
    logger.info("Checking FA for: " + str(featured_mod) + " and map " + str(mapname))

    assert featured_mod

    if version is None:
        logger.info("Version unknown, assuming latest")

    # Perform the actual comparisons and updating                    
    logger.info("Updating FA for mod: " + str(featured_mod) + ", version " + str(version))

    import client
    path(client.instance)

    # Spawn an update for the required mod
    game_updater = fa.updater.Updater(featured_mod, version, modVersions, silent=silent)
    result = game_updater.run()

    if result != fa.updater.Updater.RESULT_SUCCESS:
        return False

    # Now it's down to having the right map
    if mapname:
        if not map(mapname, silent=silent):
            return False

    if sim_mods:
        return checkMods(sim_mods)

    return True

