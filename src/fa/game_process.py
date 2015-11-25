import os

from PyQt4 import QtCore, QtGui
import config

import logging
logger = logging.getLogger(__name__)

__author__ = 'Thygrrr'


class GameArguments:
    pass


class GameProcess(QtCore.QProcess):
    def __init__(self, *args, **kwargs):
        QtCore.QProcess.__init__(self, *args, **kwargs)

    def run(self, info, arguments, detach=False, init_file=None):
            """
            Performs the actual running of ForgedAlliance.exe
            in an attached process.
            """
            executable = os.path.join(config.Settings.get('game/bin/path'),
                                      "ForgedAlliance.exe")
            command = '"' + executable + '" ' + " ".join(arguments)

            logger.info("Running FA with info: " + str(info))
            logger.info("Running FA via command: " + command)

            # Launch the game as a stand alone process
            if not instance.running():

                self.setWorkingDirectory(os.path.dirname(executable))
                if not detach:
                    self.start(command)
                else:
                    self.startDetached(executable, arguments)
                return True
            else:
                QtGui.QMessageBox.warning(None, "ForgedAlliance.exe", "Another instance of FA is already running.")
                return False

    def running(self):
        return self.state() == QtCore.QProcess.Running

    def available(self):
        if self.running():
            QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(), "ForgedAllianceForever.exe", "<b>Forged Alliance is already running.</b><br/>You can only run one instance of the game.")
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

            while self.running() and progress.isVisible():
                QtGui.QApplication.processEvents()

            progress.close()

            if self.running():
                self.kill()

            self.close()

instance = GameProcess()

