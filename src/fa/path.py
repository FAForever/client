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


import _winreg
import os
import sys
from PyQt4 import QtCore
from fa import gamepath
from fa.updater import getPathFromSettings, getPathFromSettingsSC, logger
import util

__author__ = 'Thygrrr'


def loadPathSC():
    global gamepathSC
    settings = QtCore.QSettings("ForgedAllianceForever", "FA Lobby")
    settings.beginGroup("SupremeCommanderVanilla")
    gamepathSC = settings.value("app/path")
    settings.endGroup()


def savePathSC(path):
    global gamepathSC
    gamepathSC = path
    settings = QtCore.QSettings("ForgedAllianceForever", "FA Lobby")
    settings.beginGroup("SupremeCommanderVanilla")
    settings.setValue("app/path", gamepath)
    settings.endGroup()
    settings.sync()


def loadPath():
    global gamepath
    settings = QtCore.QSettings("ForgedAllianceForever", "FA Lobby")
    settings.beginGroup("ForgedAlliance")
    gamepath = settings.value("app/path")
    settings.endGroup()


def savePath(path):
    global gamepath
    gamepath = path
    settings = QtCore.QSettings("ForgedAllianceForever", "FA Lobby")
    settings.beginGroup("ForgedAlliance")
    settings.setValue("app/path", gamepath)
    settings.endGroup()
    settings.sync()


def writeFAPathLua():
    """
    Writes a small lua file to disk that helps the new SupComDataPath.lua find the actual install of the game
    """
    name = os.path.join(util.APPDATA_DIR, u"fa_path.lua")
    code = u"fa_path = '" + gamepath.replace(u"\\", u"\\\\") + u"'\n"

    if gamepathSC:
        code = code + u"sc_path = '" + gamepathSC.replace(u"\\", u"\\\\") + u"'\n"

    lua = open(name, "w+")
    lua.write(code.encode("utf-8"))
    lua.flush()
    os.fsync(lua.fileno())  # Ensuring the file is absolutely, positively on disk.
    lua.close()


def mostProbablePaths():
    """
    Returns a list of the most probable paths where Supreme Commander: Forged Alliance might be installed
    """
    pathlist = [
        getPathFromSettings(),

        #Retail path
        os.path.expandvars("%ProgramFiles%\\THQ\\Gas Powered Games\\Supreme Commander - Forged Alliance"),

        #Direct2Drive Paths
        #... allegedly identical to impulse paths - need to confirm this

        #Impulse/GameStop Paths - might need confirmation yet
        os.path.expandvars("%ProgramFiles%\\Supreme Commander - Forged Alliance"),

        #Steam path
        os.path.expandvars("%ProgramFiles%\\Steam\\steamapps\\common\\supreme commander forged alliance")
    ]

    #Construe path from registry traces - this is not a very safe method, but it seems to work for plain installs
    try:
        regkey = "SOFTWARE\\Classes\\SCFAReplayType\\Shell\\Open\\Command"
        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, regkey)
        path = _winreg.QueryValue(key, "")
        if "ForgedAlliance.exe" in path:
            path = path[:path.rfind("bin")]
            path = path.rstrip('"/\\')
            pathlist.append(os.path.expandvars(path))
    except:
        pass

        #CAVEAT: This list is not validated
    return pathlist


def mostProbablePathsSC():
    """
    Returns a list of the most probable paths where Supreme Commander might be installed
    """
    pathlist = [
        getPathFromSettingsSC(),

        #Retail path
        os.path.expandvars("%ProgramFiles%\\THQ\\Gas Powered Games\\Supreme Commander"),

        #Direct2Drive Paths
        #... allegedly identical to impulse paths - need to confirm this

        #Impulse/GameStop Paths - might need confirmation yet
        os.path.expandvars("%ProgramFiles%\\Supreme Commander"),

        #Steam path
        os.path.expandvars("%ProgramFiles%\\Steam\\steamapps\\common\\supreme commander")
    ]

    #Construe path from registry traces - this is not a very safe method, but it seems to work for plain installs
    try:
        regkey = "SOFTWARE\\Classes\\SCReplayType\\Shell\\Open\\Command"
        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, regkey)
        path = _winreg.QueryValue(key, "")
        if "SupremeCommander.exe" in path:
            path = path[:path.rfind("bin")]
            path = path.rstrip('"/\\')
            pathlist.append(os.path.expandvars(path))
    except:
        pass

        #CAVEAT: This list is not validated
    return pathlist


def validatePath(path):
    try:
        # Supcom only supports Ascii Paths
        if not path.decode("ascii"): return False

        #We check whether the base path and a gamedata/lua.scd file exists. This is a mildly naive check, but should suffice
        if not os.path.isdir(path): return False
        if not os.path.isfile(os.path.join(path, r'gamedata', r'lua.scd')): return False

        #Reject or fix paths that end with a slash.
        #LATER: this can have all sorts of intelligent logic added
        #Suggested: Check if the files are actually the right ones, if not, tell the user what's wrong with them.
        if path.endswith("/"): return False
        if path.endswith("\\"): return False

        return True
    except:
        _, value, _ = sys.exc_info()
        logger.error(u"Path validation failed: " + unicode(value))
        return False