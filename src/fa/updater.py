
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
from types import FloatType, IntType, ListType
import logging
import urllib2
import sys
import tempfile
import json

import config
from config import Settings

from PyQt4 import QtGui, QtCore, QtNetwork

import util
import modvault


logger = logging.getLogger(__name__)

# This contains a complete dump of everything that was supplied to logOutput
debugLog = []


FormClass, BaseClass = util.loadUiType("fa/updater/updater.ui")


class UpdaterProgressDialog(FormClass, BaseClass):
    def __init__(self, parent):
        FormClass.__init__(self, parent)
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
        self.done(QtGui.QDialog.Accepted)  # equivalent to self.accept(), but clearer


def clear_log():
    global debugLog
    debugLog = []


def log(string):
    logger.debug(string)
    debugLog.append(unicode(string))


def dump_plain_text():
    return "\n".join(debugLog)


def dump_html():
    return "<br/>".join(debugLog)


# A set of exceptions we use to see what goes wrong during asynchronous data transfer waits
class UpdaterCancellation(StandardError):
    pass


class UpdaterFailure(StandardError):
    pass


class UpdaterTimeout(StandardError):
    pass


class Updater(QtCore.QObject):
    """
    This is the class that does the actual installation work.
    """
    # Network configuration
    SOCKET = 9001
    HOST = Settings.get('lobby/host')
    TIMEOUT = 20  # seconds

    # Return codes to expect from run()
    RESULT_SUCCESS = 0  # Update successful
    RESULT_NONE = -1  # Update operation is still ongoing
    RESULT_FAILURE = 1  # An error occurred during updating
    RESULT_CANCEL = 2  # User cancelled the download process
    RESULT_ILLEGAL = 3  # User has the wrong version of FA
    RESULT_BUSY = 4  # Server is currently busy
    RESULT_PASS = 5  # User refuses to update by canceling the wizard

    def __init__(self, featured_mod, version=None, mod_versions=None, sim=False, silent=False, *args, **kwargs):
        """
        Constructor
        """
        QtCore.QObject.__init__(self, *args, **kwargs)

        self.filesToUpdate = []
        self.updatedFiles = []

        self.lastData = time.time()

        self.featured_mod = featured_mod
        self.version = version
        self.mod_versions = mod_versions

        self.sim = sim
        self.mod_path = None

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
        self.progress.setWindowTitle("Updating %s" % str(self.featured_mod).upper())

        self.bytesToSend = 0

    def run(self, *args, **kwargs):
        clear_log()
        log("Update started at " + timestamp())
        log("Using appdata: " + util.APPDATA_DIR)

        self.progress.show()
        QtGui.QApplication.processEvents()

        # Actual network code adapted from previous version
        self.progress.setLabelText("Connecting to update server...")
        self.updateSocket.error.connect(self.handle_server_error)
        self.updateSocket.readyRead.connect(self.read_data_from_server)
        self.updateSocket.disconnected.connect(self.disconnected)
        self.updateSocket.error.connect(self.errored)

        self.updateSocket.connectToHost(self.HOST, self.SOCKET)

        while not (self.updateSocket.state() == QtNetwork.QAbstractSocket.ConnectedState) and self.progress.isVisible():
            QtGui.QApplication.processEvents()

        if not self.progress.wasCanceled():
            log("Connected to update server at " + timestamp())

            self.do_update()

            self.progress.setLabelText("Cleaning up.")
            self.updateSocket.close()
            self.progress.close()
        else:
            log("Cancelled connecting to server.")
            self.result = self.RESULT_CANCEL

        log("Update finished at " + timestamp())
        return self.result

    def fetch_file(self, url, to_file):
        try:
            logger.info('Updater: Downloading {}'.format(url))
            progress = QtGui.QProgressDialog()
            progress.setCancelButtonText("Cancel")
            progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
            progress.setAutoClose(True)
            progress.setAutoReset(False)

            req = urllib2.Request(url, headers={'User-Agent': "FAF Client"})
            downloaded_file = urllib2.urlopen(req)
            meta = downloaded_file.info()

            # Fix for #241, sometimes the server sends an error and no content-length.
            file_size = int(meta.getheaders("Content-Length")[0])
            progress.setMinimum(0)
            progress.setMaximum(file_size)
            progress.setModal(1)
            progress.setWindowTitle("Downloading Update")
            label = QtGui.QLabel()
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
                QtGui.QApplication.processEvents()
                read_buffer = downloaded_file.read(block_sz)
                if not read_buffer:
                    break
                file_size_dl += len(read_buffer)
                output.write(read_buffer)
                progress.setValue(file_size_dl)

            output.flush()
            os.fsync(output.fileno())
            output.close()

            shutil.move(output.name, to_file)

            if (progress.value() == file_size) or progress.value() == -1:
                logger.debug("File downloaded successfully.")
                return True
            else:
                QtGui.QMessageBox.information(None, "Aborted", "Download not complete.")
                logger.warn("File download not complete.")
                return False
        except:
            logger.error("Updater error: ", exc_info=sys.exc_info())
            QtGui.QMessageBox.information(None, "Download Failed",
                                          "The file wasn't properly sent by the server. <br/><b>Try again later.</b>")
            return False

    def update_files(self, destination, filegroup):
        """
        Updates the files in a given file group, in the destination subdirectory of the Forged Alliance path.
        If existing=True, the existing contents of the directory will be added to the current self.filesToUpdate
        list. 
        """
        QtGui.QApplication.processEvents()

        self.progress.setLabelText("Updating files: " + filegroup)
        self.destination = destination

        self.write_to_server("GET_FILES_TO_UPDATE", filegroup)
        self.wait_for_file_list()

        # Ensure our list is unique
        self.filesToUpdate = list(set(self.filesToUpdate))

        target_dir = os.path.join(util.APPDATA_DIR, destination)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        for file_to_update in self.filesToUpdate:
            md5_file = util.md5(os.path.join(util.APPDATA_DIR, destination, file_to_update))
            if md5_file is None:
                if self.version:
                    if self.featured_mod == "faf" or self.featured_mod == "ladder1v1" or filegroup == "FAF" or filegroup == "FAFGAMEDATA":
                        self.write_to_server("REQUEST_VERSION", destination, file_to_update, str(self.version))
                    else:
                        self.write_to_server("REQUEST_MOD_VERSION", destination, file_to_update,
                                             json.dumps(self.mod_versions))
                else:

                    self.write_to_server("REQUEST_PATH", destination, file_to_update)
            else:
                if self.version:
                    if self.featured_mod == "faf" or self.featured_mod == "ladder1v1" or filegroup == "FAF" or filegroup == "FAFGAMEDATA":
                        self.write_to_server("PATCH_TO", destination, file_to_update, md5_file, str(self.version))
                    else:

                        self.write_to_server("MOD_PATCH_TO", destination, file_to_update, md5_file,
                                             json.dumps(self.mod_versions))
                else:
                    self.write_to_server("UPDATE", destination, file_to_update, md5_file)

        self.wait_until_files_are_updated()

    def wait_for_sim_mod_path(self):
        """
        A simple loop that waits until the server has transmitted a sim mod path.
        """
        self.lastData = time.time()

        self.progress.setValue(0)
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)

        while self.mod_path is None:
            if self.progress.wasCanceled():
                raise UpdaterCancellation("Operation aborted while waiting for sim mod path.")

            if self.result != self.RESULT_NONE:
                raise UpdaterFailure("Operation failed while waiting for sim mod path.")

            if time.time() - self.lastData > self.TIMEOUT:
                raise UpdaterTimeout("Operation timed out while waiting for sim mod path.")

            QtGui.QApplication.processEvents()

    def wait_for_file_list(self):
        """
        A simple loop that waits until the server has transmitted a file list.
        """
        self.lastData = time.time()

        self.progress.setValue(0)
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)

        while len(self.filesToUpdate) == 0:
            if self.progress.wasCanceled():
                raise UpdaterCancellation("Operation aborted while waiting for file list.")

            if self.result != self.RESULT_NONE:
                raise UpdaterFailure("Operation failed while waiting for file list.")

            if time.time() - self.lastData > self.TIMEOUT:
                raise UpdaterTimeout("Operation timed out while waiting for file list.")

            QtGui.QApplication.processEvents()

        log("Files to update: [" + ', '.join(self.filesToUpdate) + "]")

    def wait_until_files_are_updated(self):
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

            QtGui.QApplication.processEvents()

        log("Updates applied successfully.")

    def prepare_binFAF(self):
        """
        Creates all necessary files in the binFAF folder, which contains a modified copy of all
        that is in the standard bin folder of Forged Alliance
        """
        self.progress.setLabelText("Preparing binFAF...")

        # now we check if we've got a binFAF folder
        FA_bindir = os.path.join(config.Settings.get("ForgedAlliance/app/path"), 'bin')
        FAF_dir = util.BIN_DIR

        # Try to copy without overwriting, but fill in any missing files, otherwise it might miss some files to update
        root_src_dir = FA_bindir
        root_dst_dir = FAF_dir

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

    def do_update(self):
        """ The core function that does most of the actual update work."""
        try:
            if self.sim:
                self.write_to_server("REQUEST_SIM_PATH", self.featured_mod)
                self.wait_for_sim_mod_path()
                if self.result == self.RESULT_SUCCESS:
                    if modvault.downloadMod(self.mod_path):
                        self.write_to_server("ADD_DOWNLOAD_SIM_MOD", self.featured_mod)

            else:
                # Prepare FAF directory & all necessary files
                self.prepare_binFAF()

                # Update the mod if it's requested
                if self.featured_mod == "faf" or self.featured_mod == "ladder1v1":  # HACK - ladder1v1 "is" FAF. :-)
                    self.update_files("bin", "FAF")
                    self.update_files("gamedata", "FAFGAMEDATA")
                    pass
                elif self.featured_mod:
                    self.update_files("bin", "FAF")
                    self.update_files("gamedata", "FAFGAMEDATA")
                    self.update_files("bin", self.featured_mod)
                    self.update_files("gamedata", self.featured_mod + "Gamedata")

        except UpdaterTimeout, e:
            log("TIMEOUT: {}".format(e))
            self.result = self.RESULT_FAILURE
        except UpdaterCancellation, e:
            log("CANCELLED: {}".format(e))
            self.result = self.RESULT_CANCEL
        except Exception, e:
            log("EXCEPTION: {}".format(e))
            self.result = self.RESULT_FAILURE
        else:
            self.result = self.RESULT_SUCCESS
        finally:
            self.updateSocket.close()

        # Hide progress dialog if it's still showing.
        self.progress.close()

        # Integrated handlers for the various things that could go wrong                              
        if self.result == self.RESULT_CANCEL:
            pass  # The user knows damn well what happened here.
        elif self.result == self.RESULT_PASS:
            QtGui.QMessageBox.information(QtGui.QApplication.activeWindow(), "Installation Required",
                                          "You can't play without a legal version of Forged Alliance.")
        elif self.result == self.RESULT_BUSY:
            QtGui.QMessageBox.information(QtGui.QApplication.activeWindow(), "Server Busy",
                                          "The Server is busy preparing new patch files.<br/>Try again later.")
        elif self.result == self.RESULT_FAILURE:
            failure_dialog()

        # If nothing terribly bad happened until now, the operation is a success and/or the client can display what's up
        return self.result

    @QtCore.pyqtSlot('QAbstractSocket::SocketError')
    def handle_server_error(self, socketError):
        """
        Simple error handler that flags the whole operation as failed, not very graceful but what can you do...
        """
        if socketError == QtNetwork.QAbstractSocket.RemoteHostClosedError:
            log("FA Server down: The server is down for maintenance, please try later.")

        elif socketError == QtNetwork.QAbstractSocket.HostNotFoundError:
            log("Connection to Host lost. Please check the host name and port settings.")

        elif socketError == QtNetwork.QAbstractSocket.ConnectionRefusedError:
            log("The connection was refused by the peer.")
        else:
            log("The following error occurred: %s." % self.updateSocket.errorString())

        self.result = self.RESULT_FAILURE

    def handle_action(self, bytecount, action, stream):
        """
        Process server responses by interpreting its intent and then acting upon it
        """
        log("handle_action(%s) - %d bytes" % (action, bytecount))

        if action == "PATH_TO_SIM_MOD":
            path = stream.readQString()
            self.mod_path = path
            self.result = self.RESULT_SUCCESS
            return

        elif action == "SIM_MOD_NOT_FOUND":
            log("Error: Unknown sim mod requested.")
            self.mod_path = ""
            self.result = self.RESULT_FAILURE
            return

        elif action == "LIST_FILES_TO_UP":
            self.filesToUpdate = eval(str(stream.readQString()))
            if self.filesToUpdate is None:
                self.filesToUpdate = []
            return

        elif action == "UNKNOWN_APP":
            log("Error: Unknown app/mod requested.")
            self.result = self.RESULT_FAILURE
            return

        elif action == "THIS_PATCH_IS_IN_CREATION EXCEPTION":
            log("Error: Patch is in creation.")
            self.result = self.RESULT_BUSY
            return

        elif action == "VERSION_PATCH_NOT_FOUND":
            response = stream.readQString()
            log("Error: Patch version %s not found for %s." % (self.version, response))
            self.write_to_server("REQUEST_VERSION", self.destination, response, self.version)
            return

        elif action == "VERSION_MOD_PATCH_NOT_FOUND":
            response = stream.readQString()
            log("Error: Patch version %s not found for %s." % (str(self.mod_versions), response))
            self.write_to_server("REQUEST_MOD_VERSION", self.destination, response, json.dumps(self.mod_versions))
            return

        elif action == "PATCH_NOT_FOUND":
            response = stream.readQString()
            log("Error: Patch not found for %s." % response)
            self.write_to_server("REQUEST", self.destination, response)

            return

        elif action == "UP_TO_DATE":
            response = stream.readQString()
            log("file : " + response)
            log("%s is up to date." % response)
            self.filesToUpdate.remove(str(response))
            return

        elif action == "ERROR_FILE":
            response = stream.readQString()
            log("ERROR: File not found on server : %s." % response)
            self.filesToUpdate.remove(str(response))
            self.result = self.RESULT_FAILURE
            return

        elif action == "SEND_FILE_PATH":
            path = stream.readQString()
            file_to_copy = stream.readQString()
            url = stream.readQString()

            to_file = os.path.join(util.APPDATA_DIR, str(path), str(file_to_copy))
            self.fetch_file(url, to_file)
            self.filesToUpdate.remove(str(file_to_copy))
            self.updatedFiles.append(str(file_to_copy))

        elif action == "SEND_FILE":
            path = stream.readQString()

            # HACK for feature/new-patcher
            path = util.LUA_DIR if path == "bin" else path

            file_to_copy = stream.readQString()
            size = stream.readInt()
            file_data = stream.readRawData(size)

            to_file = os.path.join(util.APPDATA_DIR, str(path), str(file_to_copy))

            write_file = QtCore.QFile(to_file)

            if write_file.open(QtCore.QIODevice.WriteOnly):
                write_file.write(file_data)
                write_file.close()
            else:  # This may or may not be desirable behavior
                logger.warn("%s is not writeable in %s. Skipping." % (file_to_copy, path))

            log("%s is copied in %s." % (file_to_copy, path))
            self.filesToUpdate.remove(str(file_to_copy))
            self.updatedFiles.append(str(file_to_copy))

        elif action == "SEND_PATCH_URL":
            destination = str(stream.readQString())
            file_to_update = str(stream.readQString())
            url = str(stream.readQString())

            to_file = os.path.join(util.CACHE_DIR, "temp.patch")
            #
            if self.fetch_file(url, to_file):
                complete_path = os.path.join(util.APPDATA_DIR, destination, file_to_update)
                self.apply_patch(complete_path, to_file)

                log("%s/%s is patched." % (destination, file_to_update))
                self.filesToUpdate.remove(str(file_to_update))
                self.updatedFiles.append(str(file_to_update))
            else:
                log("Failed to update file :'(")
        else:
            log("Unexpected server command received: " + action)
            self.result = self.RESULT_FAILURE

    def apply_patch(self, original, patch):
        to_file = os.path.join(util.CACHE_DIR, "patchedFile")
        # applying delta
        subprocess.call(['xdelta3', '-d', '-f', '-s', original, patch, to_file], stdout=subprocess.PIPE)
        shutil.copy(to_file, original)
        os.remove(to_file)
        os.remove(patch)

    @QtCore.pyqtSlot()
    def read_data_from_server(self):
        self.lastData = time.time()  # Keep resetting that timeout counter

        ins = QtCore.QDataStream(self.updateSocket)
        ins.setVersion(QtCore.QDataStream.Qt_4_2)

        while not ins.atEnd():
            # log("Bytes Available: %d" % self.updateSocket.bytesAvailable())

            # Nothing was read yet, commence a new block.
            if self.blockSize == 0:
                self.progress.reset()

                # wait for enough bytes to piece together block size information
                if self.updateSocket.bytesAvailable() < 4:
                    return

                self.blockSize = ins.readUInt32()

                if self.blockSize > 65536:
                    self.progress.setLabelText("Downloading...")
                    self.progress.setValue(0)
                    self.progress.setMaximum(self.blockSize)
                else:
                    self.progress.setValue(0)
                    self.progress.setMinimum(0)
                    self.progress.setMaximum(0)

            # Update our Gui at least once before proceeding
            # (we might be receiving a huge file and this is not the first time we get here)
            self.lastData = time.time()
            QtGui.QApplication.processEvents()

            # We have an incoming block, wait for enough bytes to accumulate
            if self.updateSocket.bytesAvailable() < self.blockSize:
                self.progress.setValue(self.updateSocket.bytesAvailable())
                return  # until later, this slot is reentrant

            # Enough bytes accumulated. Carry on.
            self.progress.setValue(self.blockSize)

            # Update our Gui at least once before proceeding (we might have to write a big file)
            self.lastData = time.time()
            QtGui.QApplication.processEvents()

            # Find out what the server just sent us, and process it.
            action = ins.readQString()
            self.handle_action(self.blockSize, action, ins)

            # Prepare to read the next block
            self.blockSize = 0

            self.progress.setValue(0)
            self.progress.setMinimum(0)
            self.progress.setMaximum(0)

    def write_to_server(self, action, *args, **kw):
        log(("write_to_server(" + action + ", [" + ', '.join(args) + "])"))
        self.lastData = time.time()

        block = QtCore.QByteArray()
        out = QtCore.QDataStream(block, QtCore.QIODevice.ReadWrite)
        out.setVersion(QtCore.QDataStream.Qt_4_2)
        out.writeUInt32(0)
        out.writeQString(action)

        for arg in args:
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
        # This isn't necessarily an error so we won't change self.result here.
        log("Disconnected from server at " + timestamp())

    @QtCore.pyqtSlot(QtNetwork.QAbstractSocket.SocketError)
    def errored(self):
        # This isn't necessarily an error so we won't change self.result here.
        log("TCP Error " + self.updateSocket.errorString())
        self.result = self.RESULT_FAILURE


def timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


# This is a pretty rough port of the old installer wizard. It works, but will need some work later
def failure_dialog():
    """
    The dialog that shows the user the log if something went wrong.
    """
    raise Exception(dump_plain_text())
