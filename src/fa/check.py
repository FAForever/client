# -------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# -------------------------------------------------------------------------------

import sys

from PyQt4 import QtGui

import fa
import modvault
from fa import writeFAPathLua, savePath

import logging
logger = logging.getLogger(__name__)


def checkMap(mapname, force=False, silent=False):
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


def check(mod, mapname=None, version=None, modVersions=None, sim_mods=None, silent=False):
    """
    This checks whether the game is properly updated and has the correct map.
    """
    logger.info("Checking FA for: " + str(mod) + " and map " + str(mapname))

    if not mod:
        QtGui.QMessageBox.warning(None, "No Mod Specified", "The application didn't specify which mod to update.")
        return False

    if not fa.gamepath:
        savePath(fa.updater.autoDetectPath())

    while not fa.updater.validatePath(fa.gamepath):
        logger.warn("Invalid path: " + str(fa.gamepath))
        wizard = fa.updater.Wizard(None)
        result = wizard.exec_()
        if not result:  # The wizard only returns successfully if the path is okay.
            return False

    # Perform the actual comparisons and updating                    
    logger.info("Updating FA for mod: " + str(mod) + ", version " + str(version))

    # Spawn an update for the required mod
    updater = fa.updater.Updater(mod, version, modVersions, silent=silent)

    result = updater.run()

    updater = None  #Our work here is done

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
        if not checkMap(mapname, silent=silent):
            return False

    if sim_mods:
        return checkMods(sim_mods)

    return True  #FA is checked and ready

