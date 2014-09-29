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


import os
from PyQt4 import QtCore, QtGui
import util

import logging
logger = logging.getLogger(__name__)

__author__ = 'Thygrrr'


class Process(QtCore.QProcess):
    def __init__(self, *args, **kwargs):
        QtCore.QProcess.__init__(self, *args, **kwargs)
        self.info = None

    @QtCore.pyqtSlot(list)
    def processGameInfo(self, message):
        """
        Processes game info events, sifting out the ones relevant to the game that's currently playing.
        If such a game is found, it will merge all its data on the first try, "completing" the game info.
        """
        if self.info and not self.info.setdefault('complete', False):
            if self.info['uid'] == message['uid']:
                if message['state'] == "playing":
                    self.info = dict(self.info.items() + message.items())   # don't we all love python?
                    self.info['complete'] = True
                    logger.info("Game Info Complete: " + str(self.info))


    def run(self, info, arguments, detach=False):
            """
            Performs the actual running of ForgedAlliance.exe
            in an attached process.
            """
            #prepare actual command for launching
            executable = os.path.join(util.BIN_DIR, "ForgedAlliance.exe")
            command = '"' + executable + '" ' + " ".join(arguments)

            logger.info("Running FA with info: " + str(info))
            logger.info("Running FA via command: " + command)
            #launch the game as a stand alone process
            if not instance.running():
                #CAVEAT: This is correct now (and was wrong in 0.4.x)! All processes are start()ed asynchronously, startDetached() would simply detach it from our QProcess object, preventing signals/slot from being emitted.
                self.info = info

                self.setWorkingDirectory(util.BIN_DIR)
                if not detach:
                    self.start(command)
                else:
                    self.startDetached(executable, arguments, util.BIN_DIR)
                return True
            else:
                QtGui.QMessageBox.warning(None, "ForgedAlliance.exe", "Another instance of FA is already running.")
                return False


    def kill(self):
        logger.warn("Process forcefully terminated.")
        self.kill()


    def running(self):
        return self.state() == QtCore.QProcess.Running


    def available(self):
        if self.running():
            QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(), "ForgedAlliance.exe", "<b>Forged Alliance is already running.</b><br/>You can only run one instance of the game.")
            return False
        return True


    def close(self):
        if self.running():
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

            if self.running():
                kill()

            self.close()

instance = Process()

