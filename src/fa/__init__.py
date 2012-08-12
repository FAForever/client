# Initialize logging system
import logging
from PyQt4 import QtCore
import os
import util
logger= logging.getLogger("faf.fa")
logger.setLevel(logging.INFO)

GPGNET_HOST = "faforever.com"
GPGNET_PORT = 7001


class Faction:
    UEF      = "/uef"
    CYBRAN   = "/cybran"
    AEON     = "/aeon"
    SERAPHIM = "/seraphim"



# This is the game path, a string pointing to the player's actual install of Forged Alliance
gamepath = None

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
    '''
    Writes a small lua file to disk that helps the new SupComDataPath.lua find the actual install of the game
    '''
    name =  os.path.join(util.APPDATA_DIR, u"fa_path.lua")
    code = u"fa_path = '" + gamepath.replace(u"\\", u"\\\\") + u"'\n"
    if (os.path.isfile(name)):
        os.remove(name)
    lua = open(name, "w")
    lua.write(code.encode("utf-8"))
    lua.flush()         
    os.fsync(lua.fileno()) # Ensuring the file is absolutely, positively on disk.
    lua.close()
        

# Initial Housekeeping
loadPath()

import exe
import maps
import replayserver
import relayserver
import updater
import upnp
