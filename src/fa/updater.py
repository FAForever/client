
"""
This is the FORGED ALLIANCE updater.

It ensures, through communication with faforever.com, that Forged Alliance is properly updated,
patched, and all required files for a given mod are installed

@author thygrrr
"""
import os
import stat
import subprocess
import time
import shutil
import logging
import urllib.request, urllib.error, urllib.parse
import sys
import tempfile
import json
import ast

import config
from config import Settings
import fafpath

from PyQt5 import QtWidgets, QtCore, QtNetwork

import util
import modvault

from api.featured_mod_updater import FeaturedModFiles, FeaturedModId
from api.sim_mod_updater import SimModFiles

logger = logging.getLogger(__name__)

# This contains a complete dump of everything that was supplied to logOutput
debugLog = []


FormClass, BaseClass = util.THEME.loadUiType("fa/updater/updater.ui")


class UpdaterProgressDialog(FormClass, BaseClass):
    def __init__(self, parent):
        BaseClass.__init__(self, parent)
        self.setupUi(self)
        self.logPlainTextEdit.setVisible(False)
        self.adjustSize()
        self.watches = []

    @QtCore.pyqtSlot(str)
    def appendLog(self, text):
        self.logPlainTextEdit.appendPlainText(text)

    @QtCore.pyqtSlot(QtCore.QObject)
    def addWatch(self, watch):
        self.watches.append(watch)
        watch.finished.connect(self.watchFinished)

    @QtCore.pyqtSlot()
    def watchFinished(self):
        for watch in self.watches:
            if not watch.isFinished():
                return
        self.done(QtWidgets.QDialog.Accepted)  # equivalent to self.accept(), but clearer


def clearLog():
    global debugLog
    debugLog = []


def log(string):
    logger.debug(string)
    debugLog.append(str(string))


def dumpPlainText():
    return "\n".join(debugLog)


def dumpHTML():
    return "<br/>".join(debugLog)


# A set of exceptions we use to see what goes wrong during asynchronous data transfer waits
class UpdaterCancellation(Exception):
    pass


class UpdaterFailure(Exception):
    pass


class UpdaterTimeout(Exception):
    pass


class Updater(QtCore.QObject):
    """
    This is the class that does the actual installation work.
    """
    # Network configuration
    TIMEOUT = 20  # seconds

    # Return codes to expect from run()
    RESULT_SUCCESS = 0  # Update successful
    RESULT_NONE = -1  # Update operation is still ongoing
    RESULT_FAILURE = 1  # An error occured during updating
    RESULT_CANCEL = 2  # User cancelled the download process
    RESULT_ILLEGAL = 3  # User has the wrong version of FA
    RESULT_BUSY = 4  # Server is currently busy
    RESULT_PASS = 5  # User refuses to update by canceling the wizard

    def __init__(self, featured_mod, version=None, modversions=None, sim=False, silent=False, *args, **kwargs):
        """
        Constructor
        """
        QtCore.QObject.__init__(self, *args, **kwargs)

        self.filesToUpdate = []
        self.updatedFiles = []

        self.lastData = time.time()

        self.featured_mod = featured_mod
        self.version = version
        self.modversions = modversions

        self.sim = sim
        self.modpath = None

        self.result = self.RESULT_NONE

        self.destination = None

        self.silent = silent
        self.progress = QtWidgets.QProgressDialog()
        if self.silent:
            self.progress.setCancelButton(None)
        else:
            self.progress.setCancelButtonText("Cancel")
        self.progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
        self.progress.setAutoClose(False)
        self.progress.setAutoReset(False)
        self.progress.setModal(1)
        self.progress.setWindowTitle("Updating %s" % str(self.featured_mod).upper())

        self.bytesToSend = 0

    def run(self, *args, **kwargs):
        clearLog()
        log("Update started at " + timestamp())
        log("Using appdata: " + util.APPDATA_DIR)

        self.progress.show()
        QtWidgets.QApplication.processEvents()

        # Actual network code adapted from previous version
        self.progress.setLabelText("Connecting to update server...")

        if not self.progress.wasCanceled():
            log("Connected to update server at " + timestamp())

            self.doUpdate()

            self.progress.setLabelText("Cleaning up.")

            self.progress.close()
        else:
            log("Cancelled connecting to server.")
            self.result = self.RESULT_CANCEL

        log("Update finished at " + timestamp())
        return self.result

    def getFilesToUpdate(self, id, version):
        return FeaturedModFiles(id, version).requestData()
    
    def getFeaturedModId(self, technicalName):
        queryDict = dict(filter = 'technicalName==' + technicalName)
        return FeaturedModId().requestData(queryDict)
    
    def requestSimPath(self, uid):
        queryDict = dict(filter = 'uid==' + uid)
        return SimModFiles().requestData(queryDict)
        
    def fetchFile(self, url, toFile):
        try:
            logger.info('Updater: Downloading {}'.format(url))
            progress = QtWidgets.QProgressDialog()
            progress.setCancelButtonText("Cancel")
            progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
            progress.setAutoClose(True)
            progress.setAutoReset(False)

            downloadedfile = urllib.request.urlopen(url)
            meta = downloadedfile.info()

            # Fix for #241, sometimes the server sends an error and no content-length.
            file_size = int(meta.get_all("Content-Length")[0])
            progress.setMinimum(0)
            progress.setMaximum(file_size)
            progress.setModal(1)
            progress.setWindowTitle("Downloading Update")
            label = QtWidgets.QLabel()
            label.setOpenExternalLinks(True)
            progress.setLabel(label)
            progress.setLabelText('Downloading FA file : <a href="' + url + '">' + url + '</a><br/>File size: ' + str(
                int(file_size / 1024 / 1024)) + ' MiB')
            progress.show()

            # Download the file as a series of up to 4 KiB chunks, then uncompress it.

            output = tempfile.NamedTemporaryFile(mode='w+b', delete=False)

            file_size_dl = 0
            block_sz = 4096

            while progress.isVisible():
                QtWidgets.QApplication.processEvents()
                if not progress.isVisible():
                    break
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
                QtWidgets.QMessageBox.information(None, "Aborted", "Download not complete.")
                logger.warning("File download not complete.")
                return False
        except:
            logger.error("Updater error: ", exc_info=sys.exc_info())
            QtWidgets.QMessageBox.information(None, "Download Failed", "The file wasn't properly sent by the server. "
                                                                       "<br/><b>Try again later.</b>")
            return False

    def updateFiles(self, destination, filegroup):
        """
        Updates the files in a given file group, in the destination subdirectory of the Forged Alliance path.
        If existing=True, the existing contents of the directory will be added to the current self.filesToUpdate
        list. 
        """
        QtWidgets.QApplication.processEvents()

        self.progress.setLabelText("Updating files: " + destination)
        self.destination = destination

        targetdir = os.path.join(util.APPDATA_DIR, destination)
        if not os.path.exists(targetdir):
            os.makedirs(targetdir)

        for fileToUpdate in filegroup:
            md5File = util.md5(os.path.join(util.APPDATA_DIR, destination, fileToUpdate['name']))
            md5NewFile = fileToUpdate['md5']
            if md5File == md5NewFile:
                self.filesToUpdate.remove(fileToUpdate)
            else:
                self.fetchFile(fileToUpdate['url'], os.path.join(util.APPDATA_DIR, destination, fileToUpdate['name']))
                self.filesToUpdate.remove(fileToUpdate)
                self.updatedFiles.append(fileToUpdate['name'])

        self.waitUntilFilesAreUpdated()


    def waitUntilFilesAreUpdated(self):
        """
        A simple loop that updates the progress bar while the server sends actual file data
        """
        self.lastData = time.time()

        self.progress.setValue(0)
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)

        while len(self.filesToUpdate) > 0:
            if self.progress.wasCanceled():
                raise UpdaterCancellation("Operation aborted while waiting for data.")

            if self.result != self.RESULT_NONE:
                raise UpdaterFailure("Operation failed while waiting for data.")

            if time.time() - self.lastData > self.TIMEOUT:
                raise UpdaterTimeout("Connection timed out while waiting for data.")

            QtWidgets.QApplication.processEvents()

        log("Updates applied successfully.")

    def prepareBinFAF(self):
        """
        Creates all necessary files in the binFAF folder, which contains a modified copy of all
        that is in the standard bin folder of Forged Alliance
        """
        self.progress.setLabelText("Preparing binFAF...")

        # now we check if we've got a binFAF folder
        FABindir = os.path.join(config.Settings.get("ForgedAlliance/app/path"), 'bin')
        FAFdir = util.BIN_DIR

        # Try to copy without overwriting, but fill in any missing files, otherwise it might miss some files to update
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
                st = os.stat(dst_file)
                os.chmod(dst_file, st.st_mode | stat.S_IWRITE)   # make all files we were considering writable, because we may need to patch them

    def doUpdate(self):
        """ The core function that does most of the actual update work."""
        try:
            if self.sim:
                if modvault.downloadMod(self.requestSimPath(self.featured_mod)):
                    self.result = self.RESULT_SUCCESS
                else:
                    self.result = self.RESULT_FAILURE

            else:
                # Prepare FAF directory & all necessary files
                self.prepareBinFAF()

                toUpdate = []
                filesToUpdateInBin = []
                filesToUpdateInGamedata = []

                # Update the mod if it's requested
                if self.featured_mod == "faf" or self.featured_mod == "ladder1v1":  # HACK - ladder1v1 "is" FAF. :-)
                    if self.version:
                        #id for faf (or ladder1v1) is 0
                        toUpdate = self.getFilesToUpdate('0', self.version)
                    else:
                        toUpdate = self.getFilesToUpdate('0', 'latest')

                    for _file in toUpdate:
                        if _file['group'] == 'bin':
                            filesToUpdateInBin.append(_file)
                        else:
                            filesToUpdateInGamedata.append(_file)

                    self.filesToUpdate = filesToUpdateInBin.copy()
                    self.updateFiles("bin", filesToUpdateInBin)
                    self.filesToUpdate = filesToUpdateInGamedata.copy()
                    self.updateFiles("gamedata", filesToUpdateInGamedata)

                elif self.featured_mod == 'fafbeta' or self.featured_mod == 'fafdevelop':
                    #no need to update faf first for these mods
                    id = self.getFeaturedModId(self.featured_mod)
                    if self.modversions:
                        modversion = sorted(self.modversions.items(), key=lambda item: item[1], reverse=True)[0][1]
                    else:
                        modversion = 'latest'
                        
                    toUpdate = self.getFilesToUpdate(id, modversion)
                    toUpdate.sort(key=lambda item: item['version'], reverse=True)
                    
                    #file lists for fafbeta and fafdevelop contain wrong version of ForgedAlliance.exe
                    if self.version:
                        faf_version = self.version
                    else:
                        faf_version = toUpdate[0]['version']
                    
                    for _file in toUpdate:
                        if _file['group'] == 'bin':
                            if _file['name'] != 'ForgedAlliance.exe':
                                filesToUpdateInBin.append(_file)
                        else:
                            filesToUpdateInGamedata.append(_file)
                    
                    self.filesToUpdate = filesToUpdateInBin.copy()
                    self.updateFiles('bin', filesToUpdateInBin)
                    self.filesToUpdate = filesToUpdateInGamedata.copy()
                    self.updateFiles('gamedata', filesToUpdateInGamedata)

                    #update proper version of bin
                    toUpdate = self.getFilesToUpdate('0', faf_version)

                    for _file in toUpdate:
                        if _file['group'] == 'bin':
                            filesToUpdateInBin.append(_file)
                    
                    self.filesToUpdate = filesToUpdateInBin.copy()
                    self.updateFiles('bin', filesToUpdateInBin)


                else:
                    #update faf first    
                    #id for faf (or ladder1v1) is 0
                    if self.version:
                        toUpdate = self.getFilesToUpdate('0', self.version)
                    else:
                        toUpdate = self.getFilesToUpdate('0', 'latest')

                    for _file in toUpdate:
                        if _file['group'] == 'bin':
                            filesToUpdateInBin.append(_file)
                        else:
                            filesToUpdateInGamedata.append(_file)
                    
                    self.filesToUpdate = filesToUpdateInBin.copy()
                    self.updateFiles("bin", filesToUpdateInBin)
                    self.filesToUpdate = filesToUpdateInGamedata.copy()
                    self.updateFiles("gamedata", filesToUpdateInGamedata)

                    filesToUpdateInBin.clear()
                    filesToUpdateInGamedata.clear()

                    #update featuredMod then
                    id = self.getFeaturedModId(self.featured_mod)
                    if self.modversions:
                        modversion = sorted(self.modversions.items(), key=lambda item: item[1], reverse=True)[0][1]
                    else:
                        modversion = 'latest'
                        
                    toUpdate = self.getFilesToUpdate(id, modversion)

                    for _file in toUpdate:
                        if _file['group'] == 'bin':
                            filesToUpdateInBin.append(_file)
                        else:
                            filesToUpdateInGamedata.append(_file)
                    
                    self.filesToUpdate = filesToUpdateInBin.copy()
                    self.updateFiles("bin", filesToUpdateInBin)
                    self.filesToUpdate = filesToUpdateInGamedata.copy()
                    self.updateFiles("gamedata", filesToUpdateInGamedata)

        except UpdaterTimeout as e:
            log("TIMEOUT: {}".format(e))
            self.result = self.RESULT_FAILURE
        except UpdaterCancellation as e:
            log("CANCELLED: {}".format(e))
            self.result = self.RESULT_CANCEL
        except Exception as e:
            log("EXCEPTION: {}".format(e))
            self.result = self.RESULT_FAILURE
        else:
            self.result = self.RESULT_SUCCESS

        # Hide progress dialog if it's still showing.
        self.progress.close()

        # Integrated handlers for the various things that could go wrong                              
        if self.result == self.RESULT_CANCEL:
            pass  # The user knows damn well what happened here.
        elif self.result == self.RESULT_PASS:
            QtWidgets.QMessageBox.information(QtWidgets.QApplication.activeWindow(), "Installation Required",
                                              "You can't play without a legal version of Forged Alliance.")
        elif self.result == self.RESULT_BUSY:
            QtWidgets.QMessageBox.information(QtWidgets.QApplication.activeWindow(), "Server Busy",
                                              "The Server is busy preparing new patch files.<br/>Try again later.")
        elif self.result == self.RESULT_FAILURE:
            failureDialog()

        # If nothing terribly bad happened until now,
        # the operation is a success and/or the client can display what's up.
        return self.result


def timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


# This is a pretty rough port of the old installer wizard. It works, but will need some work later
def failureDialog():
    """
    The dialog that shows the user the log if something went wrong.
    """
    raise Exception(dumpPlainText())
