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
#-------------------------------------------------------------------------------


from PyQt4 import QtGui
import fa
import modvault


__author__ = 'Thygrrr'

import os
import util

def init_lua_for_featured_mod(mod):
    """
    HACK for the transition period where the server still sends init_.lua files instead of the mods containing them.
    """
    repo_init_lua = os.path.join(util.REPO_DIR, mod, "init.lua")
    legacy_init_lua = os.path.join(util.LUA_DIR, "init_" + mod + ".lua")

    return repo_init_lua if os.path.exists(repo_init_lua) else legacy_init_lua


def fix_init_luas(target_dir=util.LUA_DIR):
    """
    HACK some server-side init_*.lua files expect to be executed in the current working directory, which is wrong.
    Can be removed on completion of https://github.com/FAForever/fa/issues/52
    """
    for lua_name in os.listdir(target_dir):
        with open(os.path.join(target_dir, lua_name), "r+") as lua_file:
            code = lua_file.read()
            lua_file.seek(0)
            lua_file.write(code.replace("dofile('init", "dofile(InitFileDir .. '\\\\init"))
            lua_file.truncate()


import logging
logger = logging.getLogger(__name__)

def checkLegacyMods(mods):  #mods is a dictionary of uid-name pairs
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


def checkMods(mods):
    logger.info("Updating FA for mods " + ", ".join(mods))
