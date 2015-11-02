import sys
import os
import logging

from PyQt4 import QtGui

import fa
from fa.mods import checkMods
from fa.path import writeFAPathLua, validatePath
from fa.wizards import Wizard
import mods
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

    result = QtGui.QMessageBox.question(None, "Download Map",
                                        "Seems that you don't have the map. Do you want to download it?<br/><b>" + mapname + "</b>",
                                        QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
    if result == QtGui.QMessageBox.Yes:
        if not fa.maps.downloadMap(mapname, silent=silent):
            return False
    else:
        return False

    return True


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

    # Spawn an update for the required mod
    game_updater = fa.updater.Updater(featured_mod, version, modVersions, silent=silent)
    result = game_updater.run()

    game_updater = None  #Our work here is done

    if result != fa.updater.Updater.RESULT_SUCCESS:
        return False

    logger.info("Writing fa_path.lua config file.")
    try:
        writeFAPathLua()
    except:
        logger.error("fa_path.lua can't be written: ", exc_info=sys.exc_info())
        QtGui.QMessageBox.critical(None, "Cannot write fa_path.lua",
                                   "This is a  rare error and you should report it!<br/>(open Menu BETA, choose 'Report a Bug')")
        return False


    # Now it's down to having the right map
    if mapname:
        if not map(mapname, silent=silent):
            return False

    if sim_mods:
        return checkMods(sim_mods)

    return True  #FA is checked and ready

