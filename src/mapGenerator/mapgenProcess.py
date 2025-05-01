import logging
import re

from PyQt6.QtCore import QEventLoop
from PyQt6.QtCore import QProcess
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QProgressBar
from PyQt6.QtWidgets import QProgressDialog

from src import fafpath
from src.config import setup_file_handler

from . import mapgenUtils

logger = logging.getLogger(__name__)
# Separate log file for map generator
generatorLogger = logging.getLogger(__name__)
generatorLogger.propagate = False
generatorLogger.addHandler(setup_file_handler('map_generator.log'))


class MapGeneratorProcess(object):
    def __init__(self, gen_path, out_path, args):
        self._progress = QProgressDialog()
        self._progress.setWindowTitle("Generating map, please wait...")
        self._progress.setCancelButtonText("Cancel")
        self._progress.setWindowFlags(
            Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint,
        )
        self._progress.setAutoReset(False)
        self._progress.setModal(1)
        bar = QProgressBar()
        bar.setMinimum(0)
        bar.setMaximum(0)
        bar.setTextVisible(False)
        self._progress.setBar(bar)
        self._progress.canceled.connect(self.close)
        self.progressCounter = 1

        self.map_generator_process = QProcess()
        self.map_generator_process.setWorkingDirectory(out_path)
        self.map_generator_process.readyReadStandardOutput.connect(
            self.on_log_ready,
        )
        self.map_generator_process.readyReadStandardError.connect(
            self.on_error_ready,
        )
        self._error_msgs_received = 0

        self.map_generator_process.finished.connect(self.on_exit)
        self.map_name = None

        self.java_path = fafpath.get_java_path()
        self.args = ["-jar", gen_path]
        self.args.extend(args)

        logger.info("Starting map generator with %s", " ".join((self.java_path, *self.args)))
        generatorLogger.info(">>> --------------------- MapGenerator Launch")

        self.map_generator_process.start(self.java_path, self.args)

        if not self.map_generator_process.waitForStarted(5000):
            logger.error("error starting the map generator process")
            QMessageBox.critical(
                None, "Map generator error",
                "The map generator did not start.",
            )
        else:
            self._progress.show()
            self._running = True
            self.waitForCompletion()

    @property
    def mapname(self):
        return str(self.map_name)

    def on_log_ready(self):
        standard_output = self.map_generator_process.readAllStandardOutput()
        data = standard_output.data().decode('utf8').split('\n')
        for line in data:
            if (
                re.match(mapgenUtils.generatedMapPattern, line)
                and self.map_name is None
            ):
                self.map_name = line.strip()
            if line != '':
                generatorLogger.info(line.strip())
            # Kinda fake progress bar. Better than nothing :)
            if len(line) > 4:
                self._progress.setLabelText(line[:25] + "...")

    def on_error_ready(self) -> None:
        self._error_msgs_received += 1

        message = self.map_generator_process.readAllStandardError().data().decode()
        generatorLogger.error(message)

        if self._error_msgs_received > 1:
            # Happens on wrong command line usage when the first message
            # is useful and the next is output of --help command
            return

        self.close()
        QMessageBox.critical(
            None,
            "Map generator error",
            "Something went wrong. Probably because of bad combination of "
            "generator options. Please retry with different options:\n\n"
            f"{message}",
        )

    def on_exit(self, code, status):
        self._progress.reset()
        self._running = False
        generatorLogger.info("<<< --------------------- MapGenerator Shutdown")

    def close(self):
        if self.map_generator_process.state() == QProcess.ProcessState.Running:
            logger.info("Waiting for map generator process shutdown")
            if not self.map_generator_process.waitForFinished(300):
                if self.map_generator_process.state() == QProcess.ProcessState.Running:
                    logger.error("Terminating map generator process")
                    self.map_generator_process.terminate()
                    if not self.map_generator_process.waitForFinished(300):
                        logger.error("Killing map generator process")
                        self.map_generator_process.kill()

    def waitForCompletion(self) -> None:
        '''Copied from downloadManager. I hope it's ok :)'''
        waitFlag = QEventLoop.ProcessEventsFlag.WaitForMoreEvents
        while self._running:
            QApplication.processEvents(waitFlag)
