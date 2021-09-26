import logging
import os
import re
import sys

from PyQt5 import QtCore, QtWidgets

import config
import util
from model.game import GameState

logger = logging.getLogger(__name__)

__author__ = 'Thygrrr'


class GameArguments:
    pass


class GameProcess(QtCore.QProcess):
    def __init__(self, *args, **kwargs):
        QtCore.QProcess.__init__(self, *args, **kwargs)
        self._info = None
        self._game = None
        self.gameset = None

    # Game which we track to update game info
    @property
    def game(self):
        return self._game

    @game.setter
    def game(self, value):
        if self._game is not None:
            self._game.updated.disconnect(self._trackGameUpdate)
        self._game = value

        if self._game is not None:
            self._game.updated.connect(self._trackGameUpdate)
            self._trackGameUpdate()

    # Check new games from the server to find one matching our uid
    def newServerGame(self, game):
        if not self._info or self._info['complete']:
            return
        if self._info['uid'] != game.uid:
            return
        self.game = game

    def _clearGame(self, _=None):
        self.game = None

    def _trackGameUpdate(self, _=None):
        if self.game.state == GameState.CLOSED:
            self.game = None
            return
        if self.game.state != GameState.PLAYING:
            return

        self._info.update(self.game.to_dict())
        self._info['complete'] = True
        self.game = None
        logger.info("Game Info Complete: " + str(self._info))

    def run(self, info, arguments, detach=False, init_file=None):
        """
        Performs the actual running of ForgedAlliance.exe
        in an attached process.
        """

        if self._info is not None:  # Stop tracking current game
            self.game = None

        self._info = info    # This can be none if we're running a replay
        if self._info is not None:
            self._info.setdefault('complete', False)
            if not self._info['complete']:
                uid = self._info['uid']
                try:
                    self.game = self.gameset[uid]
                except KeyError:
                    pass

        executable = os.path.join(
            config.Settings.get('game/bin/path'), "ForgedAlliance.exe",
        )
        if sys.platform == 'win32':
            command = '"{}" '.format(executable)
            command += " ".join(arguments)
        else:
            command = '{} {} "{}" '.format(
                util.wine_cmd_prefix, util.wine_exe, executable,
            )
            command += " ".join(arguments)
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
                # Remove the wrapping " at the start and end of some
                # arguments as QT will double wrap when launching
                arguments = [
                    re.sub('(^"|"$)', '', element)
                    for element in arguments
                ]
                self.startDetached(
                    executable, arguments, os.path.dirname(executable),
                )
            return True
        else:
            QtWidgets.QMessageBox.warning(
                None,
                "ForgedAlliance.exe",
                "Another instance of FA is already running.",
            )
            return False

    def running(self):
        return self.state() == QtCore.QProcess.Running

    def available(self):
        if self.running():
            QtWidgets.QMessageBox.warning(
                QtWidgets.QApplication.activeWindow(),
                "ForgedAllianceForever.exe",
                (
                    "<b>Forged Alliance is already running.</b><br/>You can "
                    "only run one instance of the game."
                ),
            )
            return False
        return True

    def close(self):
        if self.running():
            progress = QtWidgets.QProgressDialog()
            progress.setCancelButtonText("Terminate")
            progress.setWindowFlags(
                QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint,
            )
            progress.setAutoClose(False)
            progress.setAutoReset(False)
            progress.setMinimum(0)
            progress.setMaximum(0)
            progress.setValue(0)
            progress.setModal(1)
            progress.setWindowTitle("Waiting for Game to Close")
            progress.setLabelText(
                "FA Forever exited, but ForgedAlliance.exe "
                "is still running.<p align='left'><ul><b> "
                "Are you still in a game?</b><br/><br/>You "
                "may choose to:<li>press <b>ALT+TAB</b> to "
                "return to the game</li><li>kill "
                "ForgedAlliance.exe byclicking <b>Terminate"
                "</b></li></ul></p>",
            )
            progress.show()

            while self.running() and progress.isVisible():
                QtWidgets.QApplication.processEvents()

            progress.close()

            if self.running():
                self.kill()

            self.close()


instance = GameProcess()
