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





'''
This is the FORGED ALLIANCE updater.

It ensures, through communication with faforever.com, that Forged Alliance is properly updated,
patched, and all required files for a given mod are installed

@author thygrrr
'''
import _winreg

from PyQt4 import QtGui, QtCore, QtNetwork
# import bz2
# import cPickle as pickle
import os
import stat
import time
import subprocess
#import bsdiff
import shutil
from types import FloatType, IntType, ListType
import util
import logging
import urllib2
import sys
import fa
import tempfile
import json
import modvault

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# This contains a complete dump of everything that was supplied to logOutput
debugLog = []

def clearLog():
    global debugLog
    debugLog = []
    
def log(string):
    logger.debug(string)
    debugLog.append(unicode(string))

def dumpPlainText():
    return "\n".join(debugLog)

def dumpHTML():
    return "<br/>".join(debugLog)
    


# A set of exceptions we use to see what goes wrong during asynchronous data transfer waits
class UpdaterCancellation(StandardError):
    pass

class UpdaterFailure(StandardError):
    pass    

class UpdaterTimeout(StandardError):
    pass
    

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


def setPathInSettings(path):
    '''
    Stores the new path for Forged Alliance in the app settings
    '''
    settings = QtCore.QSettings("ForgedAllianceForever", "FA Lobby")
    settings.beginGroup("ForgedAlliance")
    settings.setValue("app/path", path)
    settings.endGroup()
    settings.sync()


def getPathFromSettings():    
    ''' 
    Retrieves the Path as configured in the settings 
    ''' 
    settings = QtCore.QSettings("ForgedAllianceForever", "FA Lobby")
    settings.beginGroup("ForgedAlliance")
    path = unicode(settings.value("app/path"))
    settings.endGroup()
    return path


def setPathInSettingsSC(path):
    '''
    Stores the new path for Supremene Commander in the app settings
    '''
    settings = QtCore.QSettings("ForgedAllianceForever", "FA Lobby")
    settings.beginGroup("SupremeCommanderVanilla")
    settings.setValue("app/path", path)
    settings.endGroup()
    settings.sync()


def getPathFromSettingsSC():    
    ''' 
    Retrieves the Path as configured in the settings 
    ''' 
    settings = QtCore.QSettings("ForgedAllianceForever", "FA Lobby")
    settings.beginGroup("SupremeCommanderVanilla")
    path = unicode(settings.value("app/path"))
    settings.endGroup()
    return path


def mostProbablePaths():
    '''
    Returns a list of the most probable paths where Supreme Commander: Forged Alliance might be installed
    '''
    pathlist = []
    
    pathlist.append(getPathFromSettings())

    #Retail path
    pathlist.append(os.path.expandvars("%ProgramFiles%\\THQ\\Gas Powered Games\\Supreme Commander - Forged Alliance"))

    #Direct2Drive Paths
    #... allegedly identical to impulse paths - need to confirm this

    #Impulse/GameStop Paths - might need confirmation yet
    pathlist.append(os.path.expandvars("%ProgramFiles%\\Supreme Commander - Forged Alliance"))
    
    #Steam path   
    pathlist.append(os.path.expandvars("%ProgramFiles%\\Steam\\steamapps\\common\\supreme commander forged alliance"))

    #Construe path from registry traces - this is not a very safe method, but it seems to work for plain installs 
    try :
        regkey = "SOFTWARE\\Classes\\SCFAReplayType\\Shell\\Open\\Command"
        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, regkey)
        path = _winreg.QueryValue(key, "")
        if "ForgedAlliance.exe" in path:            
            path = path[:path.rfind("bin")]
            path = path.rstrip('"/\\')
            pathlist.append(os.path.expandvars(path))    
    except :
        pass           
    
    #CAVEAT: This list is not validated
    return pathlist


def mostProbablePathsSC():
    '''
    Returns a list of the most probable paths where Supreme Commander might be installed
    '''
    pathlist = []
    
    pathlist.append(getPathFromSettingsSC())

    #Retail path
    pathlist.append(os.path.expandvars("%ProgramFiles%\\THQ\\Gas Powered Games\\Supreme Commander"))

    #Direct2Drive Paths
    #... allegedly identical to impulse paths - need to confirm this

    #Impulse/GameStop Paths - might need confirmation yet
    pathlist.append(os.path.expandvars("%ProgramFiles%\\Supreme Commander"))
    
    #Steam path   
    pathlist.append(os.path.expandvars("%ProgramFiles%\\Steam\\steamapps\\common\\supreme commander"))

    #Construe path from registry traces - this is not a very safe method, but it seems to work for plain installs 
    try :
        regkey = "SOFTWARE\\Classes\\SCReplayType\\Shell\\Open\\Command"
        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, regkey)
        path = _winreg.QueryValue(key, "")
        if "SupremeCommander.exe" in path:            
            path = path[:path.rfind("bin")]
            path = path.rstrip('"/\\')
            pathlist.append(os.path.expandvars(path))    
    except :
        pass           
    
    #CAVEAT: This list is not validated
    return pathlist


def autoDetectPath():
    for path in mostProbablePaths():
        if validatePath(path):
            return path
    
    return None
    


def validateAndAdd(path, combobox):
    '''
    Validates a given path's existence and uniqueness, then adds it to the provided QComboBox
    '''
    if validatePath(path) : 
        if (combobox.findText(path, QtCore.Qt.MatchFixedString) == -1) : 
            combobox.addItem(path)
                
                             
    
def constructPathChoices(combobox):
    '''
    Creates a combobox with all potentially valid paths for FA on this system
    '''
    combobox.clear()
    for path in mostProbablePaths():
        validateAndAdd(path, combobox)

def constructPathChoicesSC(combobox):
    '''
    Creates a combobox with all potentially valid paths for SC on this system
    '''
    combobox.clear()
    for path in mostProbablePathsSC():
        validateAndAdd(path, combobox)



class Updater(QtCore.QObject):
    '''
    This is the class that does the actual installation work.
    '''
    # Network configuration
    SOCKET  = 9001
    HOST    = "lobby.faforever.com"
    TIMEOUT = 20  #seconds

    # Return codes to expect from run()
    RESULT_SUCCESS = 0      #Update successful
    RESULT_NONE = -1        #Update operation is still ongoing
    RESULT_FAILURE = 1      #An error occured during updating
    RESULT_CANCEL = 2       #User cancelled the download process
    RESULT_ILLEGAL = 3      #User has the wrong version of FA
    RESULT_BUSY = 4      #Server is currently busy
    RESULT_PASS = 5         #User refuses to update by canceling the wizard
    
    
    def __init__(self, mod, version = None, modversions = None, sim = False, silent = False, *args, **kwargs):
        '''
        Constructor
        '''
        QtCore.QObject.__init__(self, *args, **kwargs)
        
        self.path = getPathFromSettings()

        self.filesToUpdate = []

        self.lastData = time.time()
                
        self.mod            = mod        
        self.version        = version
        self.modversions    = modversions
        
        self.sim = sim
        self.modpath = None

        
        self.blockSize = 0
        self.updateSocket = QtNetwork.QTcpSocket()
        self.updateSocket.setSocketOption(QtNetwork.QTcpSocket.KeepAliveOption, 1)
        self.updateSocket.setSocketOption(QtNetwork.QTcpSocket.LowDelayOption, 1)

        self.result = self.RESULT_NONE
        
        self.destination = None
        
        self.silent = silent
        self.progress = QtGui.QProgressDialog()
        if self.silent:
            self.progress.setCancelButton(None)
        else:
            self.progress.setCancelButtonText("Cancel")
        self.progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
        self.progress.setAutoClose(False)
        self.progress.setAutoReset(False)
        self.progress.setModal(1)
        self.progress.setWindowTitle("Updating %s" % self.mod.upper())
        
        
                
    def run(self, *args, **kwargs):
        clearLog()
        log("Update started at " + timestamp())
        log("Using game path: " + self.path)
        log("Using appdata: " + util.APPDATA_DIR)
        
        self.progress.show()
        QtGui.QApplication.processEvents()


        #Actual network code adapted from previous version
        self.progress.setLabelText("Connecting to update server...")
        self.updateSocket.error.connect(self.handleServerError)
        self.updateSocket.readyRead.connect(self.readDataFromServer)
        self.updateSocket.disconnected.connect(self.disconnected)
        self.updateSocket.error.connect(self.errored)

        self.updateSocket.connectToHost(self.HOST, self.SOCKET)                         

        while not (self.updateSocket.state() == QtNetwork.QAbstractSocket.ConnectedState) and self.progress.isVisible():
            QtGui.QApplication.processEvents()
                                                    
        if not self.progress.wasCanceled():
            log("Connected to update server at " + timestamp())
            
            self.doUpdate()        

            self.progress.setLabelText("Cleaning up.")        
            self.updateSocket.close()        
            self.progress.close()                
        else:
            log("Cancelled connecting to server.")
            self.result = self.RESULT_CANCEL
            
        log("Update finished at " + timestamp())                   
        return self.result
        
    def fetchFile(self, url, toFile):
        try:
            progress = QtGui.QProgressDialog()
            progress.setCancelButtonText("Cancel")
            progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
            progress.setAutoClose(True)
            progress.setAutoReset(False)
            
            req = urllib2.Request(url, headers={'User-Agent' : "FAF Client"})
            downloadedfile  = urllib2.urlopen(req)
            meta = downloadedfile.info()
        
            #Fix for #241, sometimes the server sends an error and no content-length.
            file_size = int(meta.getheaders("Content-Length")[0])
            progress.setMinimum(0)
            progress.setMaximum(file_size)
            progress.setModal(1)
            progress.setWindowTitle("Downloading Update")
            label = QtGui.QLabel()
            label.setOpenExternalLinks(True)
            progress.setLabel(label)
            progress.setLabelText('Downloading FA file : <a href="' + url + '">' + url + '</a><br/>File size: ' + str(int(file_size / 1024 / 1024)) + ' MiB')
            progress.show()
    
            #Download the file as a series of up to 4 KiB chunks, then uncompress it.
            
            output = tempfile.NamedTemporaryFile(mode='w+b', delete=False)

            file_size_dl = 0
            block_sz = 4096       


            while progress.isVisible():
                QtGui.QApplication.processEvents()
                read_buffer = downloadedfile.read(block_sz)
                if not read_buffer:
                    break
                file_size_dl += len(read_buffer)
                output.write(read_buffer)
                progress.setValue(file_size_dl)
        
            output.flush()
            os.fsync(output.fileno())
            output.close()
        
            shutil.move(output.name, toFile)

            
            if (progress.value() == file_size) or progress.value() == -1:            
                logger.debug("File downloaded successfully.")
                return True
            else:
                QtGui.QMessageBox.information(None, "Aborted", "Download not complete.")            
                logger.warn("File download not complete.")          
                return False  
        except:
            logger.error("Updater error: ", exc_info = sys.exc_info())
            QtGui.QMessageBox.information(None, "Download Failed", "The file wasn't properly sent by the server. <br/><b>Try again later.</b>")
            return False

        
    def updateFiles(self, destination, filegroup):        
        '''
        Updates the files in a given file group, in the destination subdirectory of the Forged Alliance path.
        If existing=True, the existing contents of the directory will be added to the current self.filesToUpdate
        list. 
        '''
        QtGui.QApplication.processEvents()

        self.progress.setLabelText("Updating files: " + filegroup)
        self.destination = destination
         
        self.writeToServer("GET_FILES_TO_UPDATE", filegroup) 
        self.waitForFileList()
        
        #Ensure our list is unique
        self.filesToUpdate = list(set(self.filesToUpdate))

        
        targetdir = os.path.join(util.APPDATA_DIR, destination)
        if not os.path.exists(targetdir) :
            os.makedirs(targetdir)           
        
        for fileToUpdate in self.filesToUpdate :
            md5File = util.md5(os.path.join(util.APPDATA_DIR, destination, fileToUpdate))              
            if md5File == None :
                if self.version :
                    if self.mod == "faf" or self.mod == "ladder1v1" or filegroup == "FAF" or filegroup == "FAFGAMEDATA" :
                        self.writeToServer("REQUEST_VERSION", destination, fileToUpdate, str(self.version))
                    else :
                        self.writeToServer("REQUEST_MOD_VERSION", destination, fileToUpdate, json.dumps(self.modversions))
                else :
                    
                    self.writeToServer("REQUEST_PATH", destination, fileToUpdate)
            else :
                if self.version :
                    if self.mod == "faf" or self.mod == "ladder1v1" or filegroup == "FAF" or filegroup == "FAFGAMEDATA" :
                        self.writeToServer("PATCH_TO", destination, fileToUpdate, md5File, str(self.version))
                    else :
                        
                        self.writeToServer("MOD_PATCH_TO", destination, fileToUpdate, md5File, json.dumps(self.modversions))
                else :
                    self.writeToServer("UPDATE", destination, fileToUpdate, md5File)  
          
        self.waitUntilFilesAreUpdated()


            
    def legalFAVersion(self):
        #Now we check the FA version
        luascd = os.path.join(self.path, 'gamedata', 'lua.scd')
                
        if not os.path.isfile(luascd):
            return False
            
        md5LUA = util.md5(luascd)
        log("lua.scd digest is %s" % md5LUA)
        return md5LUA in ["4af45c46b0abb2805bea192e6e2517d4","5cdd99bddafa38f0873bd11dd353055a","ad999839d32f4784e331e5e8be1d32a2"]  
            
    def waitForSimModPath(self):
        '''
        A simple loop that waits until the server has transmitted a sim mod path.
        '''
        self.lastData = time.time()
        
        self.progress.setValue(0)
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        
        while self.modpath == None :    
            if (self.progress.wasCanceled()) : raise UpdaterCancellation("Operation aborted while waiting for sim mod path.")
            if (self.result != self.RESULT_NONE) : raise UpdaterFailure("Operation failed while waiting for sim mod path.")
            if (time.time() - self.lastData > self.TIMEOUT) : raise UpdaterTimeout("Operation timed out while waiting for sim mod path.")
            QtGui.QApplication.processEvents()
      

    def waitForFileList(self):
        '''
        A simple loop that waits until the server has transmitted a file list.
        '''
        self.lastData = time.time()
        
        self.progress.setValue(0)
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        
        while len(self.filesToUpdate) == 0 :                    
            if (self.progress.wasCanceled()) : raise UpdaterCancellation("Operation aborted while waiting for file list.")
            if (self.result != self.RESULT_NONE) : raise UpdaterFailure("Operation failed while waiting for file list.")
            if (time.time() - self.lastData > self.TIMEOUT) : raise UpdaterTimeout("Operation timed out while waiting for file list.")
            QtGui.QApplication.processEvents()

        log("Files to update: [" + ', '.join(self.filesToUpdate) + "]")



    def waitUntilFilesAreUpdated(self):
        '''
        A simple loop that updates the progress bar while the server sends actual file data
        '''
        self.lastData = time.time()
         
        self.progress.setValue(0)
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        
        while len(self.filesToUpdate) > 0 :
            if (self.progress.wasCanceled()) : raise UpdaterCancellation("Operation aborted while waiting for data.")
            if (self.result != self.RESULT_NONE) : raise UpdaterFailure("Operation failed while waiting for data.")
            if (time.time() - self.lastData > self.TIMEOUT) : raise UpdaterTimeout("Connection timed out while waiting for data.")
            QtGui.QApplication.processEvents()        

        log("Updates applied successfully.")
    
    
    
    def prepareBinFAF(self):
        '''
        Creates all necessary files in the binFAF folder, which contains a modified copy of all
        that is in the standard bin folder of Forged Alliance
        '''
        self.progress.setLabelText("Preparing binFAF...")

        #now we check if we've got a binFAF folder
        FABindir = os.path.join(self.path, 'bin') 
        FAFdir = util.BIN_DIR  
        
        #Try to copy without overwriting, but fill in any missing files, otherwise it might miss some files to update
        root_src_dir = FABindir
        root_dst_dir = FAFdir

        for src_dir, _, files in os.walk(root_src_dir):
            dst_dir = src_dir.replace(root_src_dir, root_dst_dir)
            if not os.path.exists(dst_dir):
                os.mkdir(dst_dir)
            for file_ in files:
                src_file = os.path.join(src_dir, file_)
                dst_file = os.path.join(dst_dir, file_)
                if not os.path.exists(dst_file):
                    shutil.copy(src_file, dst_dir)                                      
                os.chmod(dst_file, stat.S_IWRITE)   # make all files we were considering writable, because we may need to patch them
               
               
    def doUpdate(self):
        ''' The core function that does most of the actual update work.'''

#        if self.legalFAVersion():
        try:
            if self.sim == True:
                self.writeToServer("REQUEST_SIM_PATH", self.mod)
                self.waitForSimModPath()
                if self.result == self.RESULT_SUCCESS:
                    if modvault.downloadMod(self.modpath):
                        self.writeToServer("ADD_DOWNLOAD_SIM_MOD", self.mod)
                        
            else:
                #Prepare FAF directory & all necessary files
                self.prepareBinFAF()
            
                #Update the mod if it's requested
                if (self.mod == "faf" or self.mod == "ladder1v1"):   #HACK - ladder1v1 "is" FAF. :-)
                    self.updateFiles("bin", "FAF")
                    self.updateFiles("gamedata", "FAFGAMEDATA")
                else:
                    self.updateFiles("bin", "FAF")
                    self.updateFiles("gamedata", "FAFGAMEDATA")
                    self.updateFiles("bin", self.mod)
                    self.updateFiles("gamedata", self.mod + "Gamedata")
            
        except UpdaterTimeout, et:
            log("TIMEOUT: %s(%s)" % (et.__class__.__name__, str(et.args)))
            self.result = self.RESULT_FAILURE
        except UpdaterCancellation, ec:
            log("CANCELLED: %s(%s)" % (ec.__class__.__name__, str(ec.args)))
            self.result = self.RESULT_CANCEL
        except Exception, e:
            log("EXCEPTION: %s(%s)" % (e.__class__.__name__, str(e.args)))
            self.result = self.RESULT_FAILURE
        else:
            self.result = self.RESULT_SUCCESS
        finally:
            self.updateSocket.close()
#        else:
#            log("Incompatible game version.")
#            self.result = self.RESULT_ILLEGAL

        #Hide progress dialog if it's still showing.
        self.progress.close()
        
        # Integrated handlers for the various things that could go wrong                              
        if (self.result == self.RESULT_CANCEL):
            pass #The user knows damn well what happened here.
        elif (self.result == self.RESULT_PASS):
            QtGui.QMessageBox.information(QtGui.QApplication.activeWindow(), "Installation Required", "You can't play without a legal version of Forged Alliance.")
        elif (self.result == self.RESULT_ILLEGAL):
            illegalDialog()
        elif (self.result == self.RESULT_BUSY):
            QtGui.QMessageBox.information(QtGui.QApplication.activeWindow(), "Server Busy", "The Server is busy preparing new patch files.<br/>Try again later.") 
        elif (self.result == self.RESULT_FAILURE):
            failureDialog()
                
        # If nothing terribly bad happened until now, the operation is a success and/or the client can display what's up.                           
        return self.result

    @QtCore.pyqtSlot('QAbstractSocket::SocketError')
    def handleServerError(self, socketError):
        '''
        Simple error handler that flags the whole operation as failed, not very graceful but what can you do...
        '''
        if socketError == QtNetwork.QAbstractSocket.RemoteHostClosedError:
            log("FA Server down: The server is down for maintenance, please try later.")

        elif socketError == QtNetwork.QAbstractSocket.HostNotFoundError:
            log("Connection to Host lost. Please check the host name and port settings.")
            
        elif socketError == QtNetwork.QAbstractSocket.ConnectionRefusedError:
            log("The connection was refused by the peer.")
        else:
            log("The following error occurred: %s." % self.updateSocket.errorString())    

        self.result = self.RESULT_FAILURE                                          
        
    def applyPatch(self, original, patch):
        toFile = os.path.join(util.CACHE_DIR, "patchedFile")
        #applying delta
        subprocess.call(['xdelta3', '-d','-f', '-s', original, patch, toFile], stdout = subprocess.PIPE)
        shutil.copy(toFile, original) 
        os.remove(toFile)
        os.remove(patch)
   
    def handleAction(self, bytecount, action, stream):  
        '''
        Process server responses by interpreting its intent and then acting upon it
        '''
        log("handleAction(%s) - %d bytes" % (action, bytecount))

        if action == "PATH_TO_SIM_MOD":
            path = stream.readQString()
            self.modpath = path
            self.result = self.RESULT_SUCCESS
            return
        
        elif action == "SIM_MOD_NOT_FOUND" :
            log("Error: Unknown sim mod requested.")
            self.modpath = ""
            self.result = self.RESULT_FAILURE
            return

        elif action == "LIST_FILES_TO_UP" :
            self.filesToUpdate = eval(str(stream.readQString()))
            if (self.filesToUpdate == None):
                self.filesToUpdate = []
            return  

        elif action == "UNKNOWN_APP" :
            log("Error: Unknown app/mod requested.")
            self.result = self.RESULT_FAILURE            
            return

        elif action == "THIS_PATCH_IS_IN_CREATION EXCEPTION" :
            log("Error: Patch is in creation.")
            self.result = self.RESULT_BUSY            
            return

        elif action == "VERSION_PATCH_NOT_FOUND" :
            response = stream.readQString()
            log("Error: Patch version %s not found for %s." % (self.version, response))
            self.writeToServer("REQUEST_VERSION", self.destination, response, self.version)
            return

        elif action == "VERSION_MOD_PATCH_NOT_FOUND" :
            response = stream.readQString()
            log("Error: Patch version %s not found for %s." % (str(self.modversions), response))
            self.writeToServer("REQUEST_MOD_VERSION", self.destination, response, json.dumps(self.modversions))
            return
        
        elif action == "PATCH_NOT_FOUND" :
            response = stream.readQString()
            log("Error: Patch not found for %s." % response)
            self.writeToServer("REQUEST", self.destination, response)
                        
            return

        elif action == "UP_TO_DATE" :
            response = stream.readQString()
            log("file : " + response)
            log("%s is up to date." % response)  
            self.filesToUpdate.remove(str(response))
            return
                    
        elif action == "ERROR_FILE" :
            response = stream.readQString()
            log("ERROR: File not found on server : %s." % response)    
            self.filesToUpdate.remove(str(response))
            self.result = self.RESULT_FAILURE            
            return        

        elif action == "SEND_FILE_PATH" :
            path = stream.readQString()
            fileToCopy = stream.readQString()
            url = stream.readQString()
            toFile = os.path.join(util.APPDATA_DIR, str(path), str(fileToCopy))
            self.fetchFile(url, toFile)
            
            #else:
             #   logger.warn("%s is not writeable in in %s. Skipping." % (fileToCopy, path)) #This may or may not be desirable behavior

           
            self.filesToUpdate.remove(str(fileToCopy)) 
                
        elif action == "SEND_FILE" :
            path = stream.readQString()
            fileToCopy = stream.readQString()
            size = stream.readInt()
            fileDatas = stream.readRawData(size)
            
            toFile = os.path.join(util.APPDATA_DIR, str(path), str(fileToCopy))
            
            writeFile = QtCore.QFile(toFile)

            if(writeFile.open(QtCore.QIODevice.WriteOnly)) :
                    writeFile.write(fileDatas)
                    writeFile.close()                
            else:
                logger.warn("%s is not writeable in in %s. Skipping." % (fileToCopy, path)) #This may or may not be desirable behavior

            log("%s is copied in %s." % (fileToCopy, path))            
            self.filesToUpdate.remove(str(fileToCopy))         
        
        elif action == "SEND_PATCH_URL" :
            destination = str(stream.readQString())
            fileToUpdate = str(stream.readQString())
            url = str(stream.readQString())
            
            toFile = os.path.join(util.CACHE_DIR, "temp.patch")
            #
            if self.fetchFile(url, toFile) :
                completePath = os.path.join(util.APPDATA_DIR, destination, fileToUpdate)
                self.applyPatch(completePath ,toFile)

                 
                log("%s/%s is patched." % (destination, fileToUpdate))             
                self.filesToUpdate.remove(str(fileToUpdate))
            else :
                log("Failed to update file :'(")
       
        
        elif action == "SEND_PATCH" :                    
            destination = str(stream.readQString())
            fileToUpdate = str(stream.readQString())
            size = stream.readInt()

            patchFile = stream.readRawData(size)
            fd = open(os.path.join(util.CACHE_DIR, "temp.patch"), 'wb')
            fd.write(patchFile)
            fd.close()

            log("patching %s/%s ..." % (destination, fileToUpdate)) 
            
            completePath = os.path.join(util.APPDATA_DIR, destination, str(fileToUpdate))
            self.applyPatch(completePath ,toFile)            

            
            log("%s/%s is patched." % (destination, fileToUpdate))             
            self.filesToUpdate.remove(str(fileToUpdate))         
        else:
            log("Unexpected server command received: " + action)
            self.result = self.RESULT_FAILURE
            


    @QtCore.pyqtSlot()
    def readDataFromServer(self):
        self.lastData = time.time()  # Keep resetting that timeout counter
        
        ins = QtCore.QDataStream(self.updateSocket)
        ins.setVersion(QtCore.QDataStream.Qt_4_2)

        while not ins.atEnd():
            #log("Bytes Available: %d" % self.updateSocket.bytesAvailable())                    

            # Nothing was read yet, commence a new block.
            if self.blockSize == 0:
                self.progress.reset()
                
                #wait for enough bytes to piece together block size information
                if self.updateSocket.bytesAvailable() < 4:                    
                    return 
                                
                self.blockSize = ins.readUInt32()
                
                if (self.blockSize > 65536):
                    self.progress.setLabelText("Downloading...")
                    self.progress.setValue(0)
                    self.progress.setMaximum(self.blockSize)
                else:
                    self.progress.setValue(0)
                    self.progress.setMinimum(0)
                    self.progress.setMaximum(0)
                            
            # Update our Gui at least once before proceeding (we might be receiving a huge file and this is not the first time we get here)   
            self.lastData = time.time()            
            QtGui.QApplication.processEvents()
                             
            #We have an incoming block, wait for enough bytes to accumulate                    
            if self.updateSocket.bytesAvailable() < self.blockSize:
                self.progress.setValue(self.updateSocket.bytesAvailable())
                return #until later, this slot is reentrant

            #Enough bytes accumulated. Carry on.
            self.progress.setValue(self.blockSize)
            
            # Update our Gui at least once before proceeding (we might have to write a big file)
            self.lastData = time.time()            
            QtGui.QApplication.processEvents()
                             
            # Find out what the server just sent us, and process it.
            action = ins.readQString()
            self.handleAction(self.blockSize, action, ins)

            # Prepare to read the next block
            self.blockSize = 0
            
            self.progress.setValue(0)
            self.progress.setMinimum(0)
            self.progress.setMaximum(0)

    def writeToServer(self, action, *args, **kw):        
        log(("writeToServer(" + action + ", [" + ', '.join(args) + "])"))
        self.lastData = time.time()
         
        block = QtCore.QByteArray()
        out = QtCore.QDataStream(block, QtCore.QIODevice.ReadWrite)
        out.setVersion(QtCore.QDataStream.Qt_4_2)
        out.writeUInt32(0)
        out.writeQString(action)
        
        for arg in args :            
            if type(arg) is IntType:
                out.writeInt(arg)
            elif isinstance(arg, basestring):
                out.writeQString(arg)
            elif type(arg) is FloatType:
                out.writeFloat(arg)
            elif type(arg) is ListType:
                out.writeQVariantList(arg)
            else:
                log("Uninterpreted Data Type: " + str(type(arg)) + " of value: " + str(arg))
                out.writeQString(str(arg))

        out.device().seek(0)
        out.writeUInt32(block.size() - 4)

        self.bytesToSend = block.size() - 4        
        self.updateSocket.write(block)


    @QtCore.pyqtSlot()
    def disconnected(self):
        #This isn't necessarily an error so we won't change self.result here.
        log("Disconnected from server at " + timestamp())


    @QtCore.pyqtSlot(QtNetwork.QAbstractSocket.SocketError)
    def errored(self, error):
        #This isn't necessarily an error so we won't change self.result here.
        log("TCP Error " + self.updateSocket.errorString())
        self.result = self.RESULT_FAILURE



def timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")
    






#This is a pretty rough port of the old installer wizard. It works, but will need some work later   
def failureDialog():
    '''
    The dialog that shows the user the log if something went wrong.
    '''
    ui = util.loadUi("fa/updater/failure.ui")
    ui.logBox.appendPlainText(dumpPlainText())
    return ui.exec_()
        
    
        
def illegalDialog():
    '''
    The dialog explains the user that his version is incompatible.
    '''
    ui = util.loadUi("fa/updater/illegal.ui")
    return ui.exec_()




class UpgradePage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(UpgradePage, self).__init__(parent)

        self.setTitle("Specify Forged Alliance folder")
        self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("fa/updater/upgrade_watermark.png"))

        layout = QtGui.QVBoxLayout()
        
        self.label = QtGui.QLabel("FAF needs a version of Supreme Commander: Forged Alliance to launch games and replays. <br/><br/><b>Please choose the installation you wish to use.</b><br/><br/>The following versions are <u>equally</u> supported:<ul><li>3596(Retail version)</li><li>3599 (Retail patch)</li><li>3603beta (GPGnet beta patch)</li><li>1.6.6 (Steam Version)</li></ul>FAF doesn't modify your existing files.<br/><br/>Select folder:")        
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.comboBox = QtGui.QComboBox()       
        self.comboBox.setEditable(True)
        constructPathChoices(self.comboBox)
        self.comboBox.currentIndexChanged.connect(self.comboChanged)
        self.comboBox.editTextChanged.connect(self.comboChanged)
        layout.addWidget(self.comboBox)
        self.setLayout(layout)

        self.browseButton = QtGui.QPushButton()
        self.browseButton.setText("Browse")       
        self.browseButton.clicked.connect(self.showChooser)
        layout.addWidget(self.browseButton )

        self.setLayout(layout)

        self.setCommitPage(True)

    @QtCore.pyqtSlot(int)
    def comboChanged(self, index):
        self.completeChanged.emit()        

    @QtCore.pyqtSlot()
    def showChooser(self):
        path = QtGui.QFileDialog.getExistingDirectory(self, "Select Forged Alliance folder", self.comboBox.currentText(), QtGui.QFileDialog.DontResolveSymlinks | QtGui.QFileDialog.ShowDirsOnly)
        if (path):
            self.comboBox.insertItem(0, path)
            self.comboBox.setCurrentIndex(0)
            self.completeChanged.emit()        
        
    def isComplete(self, *args, **kwargs):
        if validatePath(self.comboBox.currentText()):
            setPathInSettings(self.comboBox.currentText())
            return True
        else :        
            return False
    
    def validatePage(self, *args, **kwargs):
        if validatePath(self.comboBox.currentText()):
            setPathInSettings(self.comboBox.currentText())
            return True
        else :        
            return False

class UpgradePageSC(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(UpgradePageSC, self).__init__(parent)

        self.setTitle("Specify Supreme Commander folder")
        self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("fa/updater/upgrade_watermark.png"))

        layout = QtGui.QVBoxLayout()
        
        self.label = QtGui.QLabel("You can use any version of Supreme Commander.<br/><br/>FAF won't modify your existing files.<br/><br/>Select folder:")        
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.comboBox = QtGui.QComboBox()       
        self.comboBox.setEditable(True)
        constructPathChoicesSC(self.comboBox)
        self.comboBox.currentIndexChanged.connect(self.comboChanged)
        self.comboBox.editTextChanged.connect(self.comboChanged)
        layout.addWidget(self.comboBox)
        self.setLayout(layout)

        self.browseButton = QtGui.QPushButton()
        self.browseButton.setText("Browse")       
        self.browseButton.clicked.connect(self.showChooser)
        layout.addWidget(self.browseButton )

        self.setLayout(layout)

        self.setCommitPage(True)

    @QtCore.pyqtSlot(int)
    def comboChanged(self, index):
        self.completeChanged.emit()        

    @QtCore.pyqtSlot()
    def showChooser(self):
        path = QtGui.QFileDialog.getExistingDirectory(self, "Select Supreme Commander folder", self.comboBox.currentText(), QtGui.QFileDialog.DontResolveSymlinks | QtGui.QFileDialog.ShowDirsOnly)
        if (path):
            self.comboBox.insertItem(0, path)
            self.comboBox.setCurrentIndex(0)
            self.completeChanged.emit()        
        
    def isComplete(self, *args, **kwargs):
        if validatePath(self.comboBox.currentText()):
            setPathInSettingsSC(self.comboBox.currentText())
            return True
        else :        
            return False
    
    def validatePage(self, *args, **kwargs):
        if validatePath(self.comboBox.currentText()):
            setPathInSettingsSC(self.comboBox.currentText())
            return True
        else :        
            return False

class WizardSC(QtGui.QWizard):
    '''
    The actual Wizard which walks the user through the install.
    '''             
    def __init__(self, client, *args, **kwargs):
        QtGui.QWizard.__init__(self, *args, **kwargs)     
        self.client = client
        self.upgrade = UpgradePageSC()
        self.addPage(self.upgrade)
        
        self.setWizardStyle(QtGui.QWizard.ModernStyle)
        self.setWindowTitle("Supreme Commander Install Wizard")
        self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("fa/updater/upgrade_watermark.png"))
        
        self.setOption(QtGui.QWizard.NoBackButtonOnStartPage, True)
        
    
    def accept(self):
        fa.savePathSC(self.upgrade.comboBox.currentText())        
        QtGui.QWizard.accept(self)

                
class Wizard(QtGui.QWizard):
    '''
    The actual Wizard which walks the user through the install.
    '''             
    def __init__(self, client, *args, **kwargs):
        QtGui.QWizard.__init__(self, *args, **kwargs)     
        self.client = client
        self.upgrade = UpgradePage()
        self.addPage(self.upgrade)
        
        self.setWizardStyle(QtGui.QWizard.ModernStyle)
        self.setWindowTitle("FAF Install Wizard")
        self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("fa/updater/upgrade_watermark.png"))
        
        self.setOption(QtGui.QWizard.NoBackButtonOnStartPage, True)
        
    
    def accept(self):
        fa.savePath(self.upgrade.comboBox.currentText())        
        QtGui.QWizard.accept(self)

