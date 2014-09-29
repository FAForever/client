import os
import sys
import tempfile
import urllib2
from PyQt4 import QtGui, QtCore

import logging
logger = logging.getLogger(__name__)


__author__ = 'Thygrrr'

def checkForUpdates():

    pass

# This part updates the Lobby Client by downloading the latest MSI.
def fetchClientUpdate(url):
    result = QtGui.QMessageBox.question(None, "Update Needed", "Your version of FAF is outdated. You need to download and install the most recent version to connect and play.<br/><br/><b>Do you want to download and install the update now?</b>", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
    if (result == QtGui.QMessageBox.Yes):
        try:
            progress = QtGui.QProgressDialog()
            progress.setCancelButtonText("Cancel")
            progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
            progress.setAutoClose(True)
            progress.setAutoReset(False)

            req = urllib2.Request(url, headers={'User-Agent' : "FAF Client"})
            msifile  = urllib2.urlopen(req)
            meta = msifile.info()

            #Fix for #241, sometimes the server sends an error and no content-length.
            file_size = int(meta.getheaders("Content-Length")[0])
            progress.setMinimum(0)
            progress.setMaximum(file_size)
            progress.setModal(1)
            progress.setWindowTitle("Downloading Update")
            label = QtGui.QLabel()
            label.setOpenExternalLinks(True)
            progress.setLabel(label)
            progress.setLabelText('Downloading the latest version of <b>Forged Alliance Forever</b><br/><a href="' + url + '">' + url + '</a><br/>File size: ' + str(int(file_size / 1024 / 1024)) + ' MiB')
            progress.show()

            #Download the file as a series of up to 4 KiB chunks, then uncompress it.
            output = tempfile.NamedTemporaryFile(mode='w+b', suffix=".msi", delete=False)

            file_size_dl = 0
            block_sz = 4096

            while progress.isVisible():
                QtGui.QApplication.processEvents()
                read_buffer = msifile.read(block_sz)
                if not read_buffer:
                    break
                file_size_dl += len(read_buffer)
                output.write(read_buffer)
                progress.setValue(file_size_dl)

            output.flush()
            os.fsync(output.fileno())
            output.close()

            if (progress.value() == file_size):
                logger.debug("MSI download successful.")
                import subprocess
                command = r'msiexec /i "{msiname}" & del "{msiname}"'.format(msiname = output.name)
                logger.debug(r'Running command: ' + command)
                subprocess.Popen(command, shell=True)
            else:
                QtGui.QMessageBox.information(None, "Aborted", "Update download not complete.")
                logger.warn("MSI download not complete.")
        except:
            logger.error("Updater error: ", exc_info = sys.exc_info())
            QtGui.QMessageBox.information(None, "Download Failed", "The file wasn't properly sent by the server. <br/><b>Try again later.</b>")




