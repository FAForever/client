import os
import sys

from PyQt4 import QtCore, QtGui
import config
import re

import util
import logging
logger = logging.getLogger(__name__)

__author__ = 'Thygrrr'


class GameArguments:
    pass


class GameProcess(QtCore.QProcess):
    def __init__(self, *args, **kwargs):
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
                    self.info = dict(list(self.info.items()) + list(message.items()))
                    self.info['complete'] = True
                    logger.info("Game Info Complete: " + str(self.info))

    def run(self, info, arguments, detach=False, init_file=None):
            """
            Performs the actual running of ForgedAlliance.exe
            in an attached process.
            """
            self.info = info

            executable = os.path.join(config.Settings.get('game/bin/path'),
                                      "ForgedAlliance.exe")
            if sys.platform == 'win32':
                command = '"' + executable + '" ' + " ".join(arguments)
            else:
                command = util.wine_cmd_prefix + " " + util.wine_exe + ' "' + executable + '" ' + " ".join(arguments)
                if util.wine_prefix:
                    wine_env = QtCore.QProcessEnvironment.systemEnvironment()
                    wine_env.insert("WINEPREFIX", util.wine_prefix)
                    QtCore.QProcess.setProcessEnvironment(self, wine_env)
            logger.info("Running FA with info: " + str(info))
            logger.info("Running FA via command: " + command)
            logger.info("Running FA via executable: " + executable)

            # Launch the game as a stand alone process
            if not instance.running():

                self.setWorkingDirectory(os.path.dirname(executable))
                if not detach:
                    self.start(command)
                else:
                    # Remove the wrapping " at the start and end of some arguments as QT will double wrap when launching
                    arguments = [re.sub('(^"|"$)', '', element) for element in arguments]
                    self.startDetached(executable, arguments, os.path.dirname(executable))
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

