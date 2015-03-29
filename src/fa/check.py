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
import os
import logging

from PyQt4 import QtGui

from fa.mods import checkMods
from fa.path import writeFAPathLua, validatePath
from fa.wizards import Wizard
from fa.game_version import GameVersion
from fa.binary import Updater
from git import Repository

import mods
import fa.path
from config import Settings

logger = logging.getLogger(__name__)


def map(mapname, force = False, silent = False):
    """
    Assures that the map is available in FA, or returns false.
    """
    logger.info("Updating FA for map: " + str(mapname))

    if fa.maps.isMapAvailable(mapname):
        logger.info("Map is available.")
        return True

    if force:
        return fa.maps.downloadMap(mapname, silent = silent)

    result = QtGui.QMessageBox.question(None, "Download Map",
                                        "Seems that you don't have the map. Do you want to download it?<br/><b>" + mapname + "</b>",
                                        QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
    if result == QtGui.QMessageBox.Yes:
        if not fa.maps.downloadMap(mapname, silent = silent):
            return False
    else:
        return False

    return True


def featured_mod(featured_mod, version):
    pass


def sim_mod(sim_mod, version):
    pass


def path(parent):
    if not fa.path.getGameFolderFA():
        fa.path.setGameFolderFA(fa.path.autoDetectPath())

    while not validatePath(fa.path.getGameFolderFA()):
        logger.warn("Invalid path: " + str(fa.path.getGameFolderFA()))
        wizard = Wizard(None)
        result = wizard.exec_()
        if result == QtGui.QWizard.Rejected:
            return False

    logger.info("Writing fa_path.lua config file.")
    writeFAPathLua()


def game(parent, game_version):
    if not game_version.is_stable:
        logger.info("Unstable game version")
        # TODO: Show some dialog here

    if not game_version.is_trusted:
        logger.info("Untrusted repositories")
        # TODO: Show some dialog here

    engine_repo = game_version.engine_repo
    if not engine_repo.has_version(game_version.engine):
        logger.info("We don't have the required engine version")
        logger.debug("Requested version %s" % game_version.engine)
        logger.debug("Repo: %s" % game_version.engine_repo.path)
        return False
    else:
        engine_repo.checkout_version(game_version.engine)
        updater = Updater(engine_repo, parent)
        game_path = os.path.join(fa.path.getGameFolderFA(), 'bin')
        if not updater.check_up_to_date(game_path):
            updater.patch_forged_alliance(os.path.join(fa.path.getGameFolderFA(), 'bin'))

    main_mod_repo = game_version.main_mod_repo
    if not main_mod_repo.has_version(game_version.main_mod.version):
        logger.info("We don't have the required game version")
        return False
    else:
        main_mod_repo.checkout_version(game_version.main_mod.version)

    return True


def check(featured_mod, mapname = None, version = None, modVersions = None, sim_mods = None, silent = False):
    """
    This checks whether the mods are properly updated and player has the correct map.
    """
    logger.info("Checking FA for: " + str(featured_mod) + " and map " + str(mapname))

    assert featured_mod

    if version is None:
        logger.fatal("Cannot update to an unknown version of FA")
        return False

    # Perform the actual comparisons and updating
    logger.info("Updating FA for mod: " + str(featured_mod) + ", version " + str(version))

    # Spawn an update for the required mod
    legacy_versions, repo_versions = mods.filter_mod_versions(modVersions, mods.MOD_UID_TO_REPO)
    legacy_featured, repo_featured = mods.filter_featured_mods(featured_mod, mods.FEATURED_MOD_TO_REPO)

    game_updater = fa.updater.Updater(legacy_featured, version, legacy_versions, silent = silent)
    result = game_updater.run()

    if repo_featured:
        import featured
        for featured_mod in repo_featured:
            featured.checkout_featured_mod(featured_mod, repo_featured[featured_mod]['url'], repo_featured[featured_mod]['target'])


    game_updater = None  # Our work here is done

    if result != fa.updater.Updater.RESULT_SUCCESS:
        return False

    logger.info("Writing fa_path.lua config file.")
    try:
        writeFAPathLua()
    except:
        logger.error("fa_path.lua can't be written: ", exc_info = sys.exc_info())
        QtGui.QMessageBox.critical(None, "Cannot write fa_path.lua",
                                   "This is a  rare error and you should report it!<br/>(open Menu BETA, choose 'Report a Bug')")
        return False


    # Now it's down to having the right map
    if mapname:
        if not map(mapname, silent = silent):
            return False

    if sim_mods:
        return checkMods(sim_mods)

    return True  # FA is checked and ready

