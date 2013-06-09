#-------------------------------------------------------------------------------
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

import os

from PyQt4 import QtCore, QtGui

from util import strtodate, datetostr, now
import util
import logging
from vault import luaparser

logger = logging.getLogger("faf.modvault")
logger.setLevel(logging.DEBUG)

MODFOLDER = os.path.join(util.PERSONAL_DIR, "My Games", "Gas Powered Games", "Supreme Commander Forged Alliance", "Mods")
MODVAULT_DOWNLOAD_ROOT = "http://www.faforever.com/faf/modvault/"
LOCALFOLDER = os.path.join(*os.path.split(os.path.expandvars("%APPDATA%"))[:-1])
LOCALFOLDER = os.path.join(LOCALFOLDER, "Local","Gas Powered Games","Supreme Commander Forged Alliance")
PREFSFILENAME = os.path.join(LOCALFOLDER, "game.prefs")
        
def modToFilename(mod):
    return os.path.join(MODFOLDER, mod.name)

def isModFolderValid(folder):
    return os.path.exists(os.path.join(folder,"mod_info.lua"))

def parseModInfo(folder):
    if not isModFolderValid(folder):
        return None
    modinfofile = luaparser.luaParser(os.path.join(folder,"mod_info.lua"))
    modinfo = modinfofile.parse({"name":"name","uid":"uid","version":"version","description":"description","ui_only":"ui_only"},
                                {"version":1,"ui_only":'false',"description":""})
    modinfo["ui_only"] = (modinfo["ui_only"] == 'true')
    return (modinfofile, modinfo)

def getModfromName(modname): # returns a dict with the relevant mod info
    r = parseModInfo(os.path.join(MODFOLDER,modname))
    if r == None:
        logger.debug("mod_info.lua not found in %s folder" % modname)
        return None
    f, info = r
    if f.error:
        logger.debug("Error in parsing %s/mod_info.lua" % mod)
        return None
    return info

def getInstalledMods(): #returns a list of names of installed mods
        mods = []
        if os.path.isdir(MODFOLDER):
            mods = os.listdir(MODFOLDER)
        return mods

def getActiveMods(uimods=None): # returns a list of dicts containing information of the mods
    """uimods:
        None - return all active mods
        True - only return active UI Mods
        False - only return active non-UI Mods
    """
    l = luaparser.luaParser(PREFSFILENAME)
    modlist = l.parse({"active_mods":"active_mods"},{"active_mods":{}})["active_mods"]
    uids = [uid for uid,b in modlist.items() if b == 'true']
    modnames = getInstalledMods()

    allmods = []
    for modname in modnames:
        m = getModfromName(modname)
        if m != None:
            if ((uimods == True and m['ui_only']) or (uimods == False and not m['ui_only'])):
                allmods.append(m)

    active_mods = [m for m in allmods if m['uid'] in uids]
    return active_mods
        
            



    
    
