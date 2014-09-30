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


# Initialize logging system
from PyQt4 import QtCore
import os
import util

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

GPGNET_HOST = "faforever.com"
GPGNET_PORT = 8000


# We only want one instance of Forged Alliance to run, so we use a singleton here (other modules may wish to connect to its signals so it needs persistence)
from process import instance as instance
from play import play as play


# This is the game path, a string pointing to the player's actual install of Forged Alliance
gamepath = None


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


# Initial Housekeeping
loadPath()
loadPathSC()

import check
import maps
import replayserver
import relayserver
import proxies
import updater
import upnp
import faction
