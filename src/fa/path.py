import os
import sys
from PyQt4 import QtCore
import logging
import util

logger = logging.getLogger(__name__)

def steamPath():
    try:
        import _winreg
        steam_key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, "Software\\Valve\\Steam", 0, (_winreg.KEY_WOW64_64KEY + _winreg.KEY_ALL_ACCESS))
        return _winreg.QueryValueEx(steam_key, "SteamPath")[0].replace("/", "\\")
    except StandardError, e:
        return None

def writeFAPathLua():
    """
    Writes a small lua file to disk that helps the new SupComDataPath.lua find the actual install of the game
    """
    name = os.path.join(util.APPDATA_DIR, u"fa_path.lua")
    gamepath_fa = util.settings.value("ForgedAlliance/app/path", type=str)

    code = u"fa_path = '" + gamepath_fa.replace(u"\\", u"\\\\") + u"'\n"

    gamepath_sc = util.settings.value("SupremeCommander/app/path", type=str)
    if gamepath_sc:
        code = code + u"sc_path = '" + gamepath_sc.replace(u"\\", u"\\\\") + u"'\n"

    with open(name, "w+") as lua:
        lua.write(code.encode("utf-8"))
        lua.flush()
        os.fsync(lua.fileno())  # Ensuring the file is absolutely, positively on disk.


def typicalForgedAlliancePaths():
    """
    Returns a list of the most probable paths where Supreme Commander: Forged Alliance might be installed
    """
    pathlist = [
        util.settings.value("ForgedAlliance/app/path", "", type=str),

        #Retail path
        os.path.expandvars("%ProgramFiles%\\THQ\\Gas Powered Games\\Supreme Commander - Forged Alliance"),

        #Direct2Drive Paths
        #... allegedly identical to impulse paths - need to confirm this

        #Impulse/GameStop Paths - might need confirmation yet
        os.path.expandvars("%ProgramFiles%\\Supreme Commander - Forged Alliance"),

        #Guessed Steam path
        os.path.expandvars("%ProgramFiles%\\Steam\\steamapps\\common\\supreme commander forged alliance")
    ]

    #Registry Steam path
    steam_path = steamPath()
    if steam_path:
        pathlist.append(os.path.join(steam_path, "SteamApps", "common", "Supreme Commander Forged Alliance"))

    return filter(validatePath, pathlist)


def typicalSupComPaths():
    """
    Returns a list of the most probable paths where Supreme Commander might be installed
    """
    pathlist = [
        util.settings.value("SupremeCommander/app/path", None, type=str),

        #Retail path
        os.path.expandvars("%ProgramFiles%\\THQ\\Gas Powered Games\\Supreme Commander"),

        #Direct2Drive Paths
        #... allegedly identical to impulse paths - need to confirm this

        #Impulse/GameStop Paths - might need confirmation yet
        os.path.expandvars("%ProgramFiles%\\Supreme Commander"),

        #Guessed Steam path
        os.path.expandvars("%ProgramFiles%\\Steam\\steamapps\\common\\supreme commander")
    ]

    #Registry Steam path
    steam_path = steamPath()
    if steam_path:
        pathlist.append(os.path.join(steam_path, "SteamApps", "common", "Supreme Commander"))

    return filter(validatePath, pathlist)


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
