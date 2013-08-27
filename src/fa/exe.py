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





from PyQt4 import QtCore, QtGui
import os
import util
import fa
import modvault


from fa import logger, writeFAPathLua, savePath
from replayparser import replayParser
from main import sys
import json


class Process(QtCore.QProcess):    
    def __init__(self, mod=None, uid=None, *args, **kwargs):        
        QtCore.QProcess.__init__(self, *args, **kwargs)
        self.info = None

    @QtCore.pyqtSlot(list)
    def processGameInfo(self, message):
        '''
        Processes game info events, sifting out the ones relevant to the game that's currently playing.
        If such a game is found, it will merge all its data on the first try, "completing" the game info.
        '''
        if self.info and not self.info.setdefault('complete', False):                
            if self.info['uid'] == message['uid']:
                if message['state'] == "playing":
                    self.info = dict(self.info.items() + message.items())   #don't we all love python?
                    self.info['complete'] = True
                    logger.info("Game Info Complete: " + str(self.info))
        
        

# We only want one instance of Forged Alliance to run, so we use a singleton here (other modules may wish to connect to its signals so it needs persistence)
instance = Process()


def kill():
    logger.warn("Process forcefully terminated.")
    instance.kill()
    

def running():
    return (instance.state() == Process.Running)
    
    
    
def available():
    if running():
        QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(), "ForgedAlliance.exe", "<b>Forged Alliance is already running.</b><br/>You can only run one instance of the game.")
        return False
    return True
    
    
    
def close():
    if running():            
        progress = QtGui.QProgressDialog()
        progress.setCancelButtonText("Terminate")
        progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setMinimum(0)
        progress.setMaximum(0)
        progress.setValue(0)
        progress.setModal(1)
        progress.setWindowTitle("Waiting for Game to Close")
        progress.setLabelText("FA Forever exited, but ForgedAlliance.exe is still running.<p align='left'><ul><b>Are you still in a game?</b><br/><br/>You may choose to:<li>press <b>ALT+TAB</b> to return to the game</li><li>kill ForgedAlliance.exe by clicking <b>Terminate</b></li></ul></p>")
        progress.show()    
                
        while running() and progress.isVisible():                
            QtGui.QApplication.processEvents()
                            
        progress.close()
              
        if running():
            kill()
        
        instance.close()    
    
    
    
def __run(info, arguments, detach = False):
        '''
        Performs the actual running of ForgedAlliance.exe
        in an attached process.
        '''        
        #prepare actual command for launching
        executable = os.path.join(util.BIN_DIR, "ForgedAlliance.exe")
        command = '"' + executable + '" ' + " ".join(arguments) 
        
        logger.info("Running FA with info: " + str(info))
        logger.info("Running FA via command: " + command)
        #launch the game as a stand alone process            
        if (not running()):
            #CAVEAT: This is correct now (and was wrong in 0.4.x)! All processes are start()ed asynchronously, startDetached() would simply detach it from our QProcess object, preventing signals/slot from being emitted.
            instance.info = info
            
            instance.setWorkingDirectory(util.BIN_DIR)
            if not detach:
                instance.start(command)
            else:  
                instance.startDetached(executable, arguments, util.BIN_DIR)
            return True
        else:
            QtGui.QMessageBox.warning(None, "ForgedAlliance.exe", "Another instance of FA is already running.")
            return False

def replay(source, detach = False):
    '''
    Launches FA streaming the replay from the given location. Source can be a QUrl or a string
    '''
    logger.info("fa.exe.replay(" + str(source) + ", detach = " + str(detach))
    
    if (available()):
        version = None
        featured_mod_versions = None
        arg_string = None
        # Convert strings to URLs
        if isinstance(source, basestring):
            if os.path.isfile(source):
                if source.endswith(".fafreplay"):   # the new way of doing things
                    replay = open(source, "rt")
                    info = json.loads(replay.readline())
                    
                    binary = QtCore.qUncompress(QtCore.QByteArray.fromBase64(replay.read()))
                    logger.info("Extracted " + str(binary.size()) + " bytes of binary data from .fafreplay.")
                    replay.close()
                    
                    scfa_replay = QtCore.QFile(os.path.join(util.CACHE_DIR, "temp.scfareplay"))
                    scfa_replay.open(QtCore.QIODevice.WriteOnly | QtCore.QIODevice.Truncate)                
                    scfa_replay.write(binary)
                    scfa_replay.flush()
                    scfa_replay.close()                    
                                
                    mapname = info.get('mapname', None)
                    mod = info['featured_mod']        
                    featured_mod_versions = info.get('featured_mod_versions', None)
                    arg_string = scfa_replay.fileName()
                    
                    parser = replayParser(arg_string)
                    version = parser.getVersion() 
                    
                    if mod == "gw":
                        infoReplayGW = fa.gwreplayinfo.GWReplayInfo(info['uid'])
                        result = infoReplayGW.run()
                        if (result != fa.gwreplayinfo.GWReplayInfo.RESULT_SUCCESS):
                            logger.info("We don't have the info necessary for GW")
                            return False                  

                        logger.info("Writing GW game table file.")

                elif source.endswith(".scfareplay"):   # compatibility mode
                    filename = os.path.basename(source)
                    if len(filename.split(".")) > 2:                        
                        mod = filename.rsplit(".", 2)[1]
                        logger.info("mod guessed from " + source + " is " + mod)
                    else:
                        mod = "faf" #TODO: maybe offer a list of mods for the user.
                        logger.warn("no mod could be guessed, using fallback ('faf') ")
                                    
                    mapname = None
                    arg_string = source
                    parser = replayParser(arg_string)
                    version = parser.getVersion()
                else:
                    QtGui.QMessageBox.critical(None, "FA Forever Replay", "Sorry, FAF has no idea how to replay this file:<br/><b>" + source + "</b>")        
                
                logger.info("Replaying " + str(arg_string) + " with mod " + str(mod) + " on map " + str(mapname))
            else:
                source = QtCore.QUrl(source)    #Try to interpret the string as an actual url, it may come from the command line
        
        if isinstance(source, QtCore.QUrl):
            url = source
            #Determine if it's a faflive url
            if url.scheme() == "faflive":
                mod = url.queryItemValue("mod")
                mapname = url.queryItemValue("map")                
                # whip the URL into shape so ForgedAlliance.exe understands it
                arg_url = QtCore.QUrl(url)
                arg_url.setScheme("gpgnet")
                arg_url.setEncodedQuery(QtCore.QByteArray())
                arg_string = arg_url.toString()
            else:
                QtGui.QMessageBox.critical(None, "FA Forever Replay", "App doesn't know how to play replays from that scheme:<br/><b>" + url.scheme() + "</b>")        
                return False                        

        # We couldn't construct a decent argument format to tell ForgedAlliance for this replay
        if not arg_string:
            QtGui.QMessageBox.critical(None, "FA Forever Replay", "App doesn't know how to play replays from that source:<br/><b>" + str(source) + "</b>")
            return False
            
        # Launch preparation: Start with an empty arguments list
        arguments = []    
        arguments.append('/replay')         
        arguments.append(arg_string)  
        #arguments.append('/sse2')
        #arguments.append('/networksafe')                        
                        
        #Proper mod loading code
        if not '/init' in arguments:
            arguments.append('/init')
            arguments.append("init_" + mod + ".lua")
                                        
        #disable bug reporter and movies
        arguments.append('/nobugreport')

        #log file
        arguments.append("/log")
        arguments.append('"' + util.LOG_FILE_REPLAY + '"')

        # Update the game appropriately
        if not check(mod, mapname, version, featured_mod_versions):
            logger.error("Can't watch replays without an updated Forged Alliance game!")
            return False        

        if mod == "gw":
        # in case of GW, we need to alter the scenario for support AIs
            if not fa.maps.gwmap(info['mapname']):
                logger.error("You don't have the required map.")
                return    

        # Finally, run executable        
        if __run(None, arguments, detach):
            logger.info("Viewing Replay.")
            return True
        else:
            logger.error("Replaying failed.")
            return False
            
    
    
def play(info, port, log = False, arguments = None, gw = False):
    '''
    Launches FA with all necessary arguments.
    '''
    if not arguments:
        arguments = []
            
    #Proper mod loading code, but allow for custom init by server
    if not '/init' in arguments:
        arguments.append('/init')
        arguments.append("init_" + info['featured_mod'] + ".lua")
                    
    #log file

    if log :
        arguments.append("/log")
        arguments.append('"' + util.LOG_FILE_GAME + '"')
    
    #live replay
    
    arguments.append('/savereplay')
    if gw == False :
        arguments.append('gpgnet://'+'localhost'+'/' + str(info['uid']) + "/" + str(info['recorder']) + '.SCFAreplay')
    else :
        arguments.append('gpgnet://'+'localhost'+'/' + str(info['uid']) + "/" + str(info['recorder']) + '.GWreplay')
        
    #disable bug reporter
    arguments.append('/nobugreport')
    #arguments.append('/sse2')
    #arguments.append('/networksafe')
        
    #gpg server
    arguments.append('/gpgnet 127.0.0.1:' + str(port))
        
                    
    return __run(info, arguments)
        


def checkMap(mapname, force = False):
    '''
    Assures that the map is available in FA, or returns false.
    '''
    logger.info("Updating FA for map: " + str(mapname))

    if fa.maps.isMapAvailable(mapname):
        logger.info("Map is available.")
        return True
    
    if force:        
        return fa.maps.downloadMap(mapname)
        
    result = QtGui.QMessageBox.question(None, "Download Map", "Seems that you don't have the map. Do you want to download it?<br/><b>" + mapname + "</b>", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
    if result == QtGui.QMessageBox.Yes :
        if not fa.maps.downloadMap(mapname):
            return False
    else:
        return False
    
    return True

def checkMods(mods): #mods is a dictionary of uid-name pairs
    '''
    Assures that the specified mods are available in FA, or returns False.
    Also sets the correct active mods in the ingame mod manager.
    '''
    logger.info("Updating FA for mods %s" % ", ".join(mods))
    to_download = []
    inst = modvault.getInstalledMods()
    uids = [mod.uid for mod in inst]
    for uid in mods:
        if uid not in uids:
            to_download.append(mods[uid])

    for modname in to_download:
        result = QtGui.QMessageBox.question(None, "Download Mod", "Seems that you don't have this mod. Do you want to download it?<br/><b>" + modname + "</b>", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if result == QtGui.QMessageBox.Yes:
            if not modvault.downloadMod(modname):
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
            QtGui.QMessageBox.warning(None, "Mod not Found", "%s was apparently not installed correctly. Please check this." % mods[uid])
            return
        actual_mods.append(uids[uid])
    if not modvault.setActiveMods(actual_mods):
        logger.warn("Couldn't set the active mods in the game.prefs file")
        return False

    return True
    
def check(mod, mapname = None, version = None, modVersions = None, sim_mods = None):
    '''
    This checks whether the game is properly updated and has the correct map.
    '''
    logger.info("Checking FA for: " + str(mod) + " and map " + str(mapname))
    
    if not mod:
        QtGui.QMessageBox.warning(None, "No Mod Specified", "The application didn't specify which mod to update.")
        return False
        
    if not fa.gamepath:
        savePath(fa.updater.autoDetectPath())
               
    while (not fa.updater.validatePath(fa.gamepath)):
        logger.warn("Invalid path: " + str(fa.gamepath))
        wizard = fa.updater.Wizard(None)
        result = wizard.exec_()
        if not result:  # The wizard only returns successfully if the path is okay.
            return False
    
    # Perform the actual comparisons and updating                    
    logger.info("Updating FA for mod: " + str(mod) + ", version " + str(version))

    # Spawn an update for the required mod
    updater = fa.updater.Updater(mod, version, modVersions)
            
    result = updater.run()

    updater = None #Our work here is done

    if (result != fa.updater.Updater.RESULT_SUCCESS):
        return False 

    logger.info("Writing fa_path.lua config file.")
    try:
        writeFAPathLua()
    except:
        logger.error("fa_path.lua can't be written: ", exc_info=sys.exc_info())
        QtGui.QMessageBox.critical(None, "Cannot write fa_path.lua", "This is a  rare error and you should report it!<br/>(open Menu BETA, choose 'Report a Bug')")             
        return False
        

    # Now it's down to having the right map
    if mapname:
        if not checkMap(mapname):
            return False

    if sim_mods:
        return checkMods(sim_mods)
        
    return True #FA is checked and ready
        
