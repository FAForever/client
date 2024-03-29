import logging
import re

from PyQt5.QtCore import QEventLoop, QProcess, Qt
from PyQt5.QtWidgets import QApplication, QMessageBox, QProgressDialog

import fafpath
from config import setup_file_handler

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
            Qt.CustomizeWindowHint | Qt.WindowTitleHint,
        )
        self._progress.setAutoReset(False)
        self._progress.setModal(1)
        self._progress.setMinimum(0)
        self._progress.setMaximum(30)
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
        self.map_generator_process.finished.connect(self.on_exit)
        self.map_name = None

        self.java_path = fafpath.get_java_path()
        self.args = ["-jar", gen_path]
        self.args.extend(args)

        logger.info(
            "Starting map generator with {} {}"
            .format(self.java_path, " ".join(self.args)),
        )
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
                self.progressCounter += 1
                self._progress.setValue(self.progressCounter)

    def on_error_ready(self):
        standard_error = str(self.map_generator_process.readAllStandardError())
        for line in standard_error.splitlines():
            generatorLogger.error("Error: " + line)
        self.close()
        QMessageBox.critical(
            None,
            "Map generator error",
            "Something went wrong. Probably because of bad combination of "
            "generator options. Please retry with different options",
        )

    def on_exit(self, code, status):
        self._progress.reset()
        self._running = False
        generatorLogger.info("<<< --------------------- MapGenerator Shutdown")

    def close(self):
        if self.map_generator_process.state() == QProcess.Running:
            logger.info("Waiting for map generator process shutdown")
            if not self.map_generator_process.waitForFinished(300):
                if self.map_generator_process.state() == QProcess.Running:
                    logger.error("Terminating map generator process")
                    self.map_generator_process.terminate()
                    if not self.map_generator_process.waitForFinished(300):
                        logger.error("Killing map generator process")
                        self.map_generator_process.kill()

    def waitForCompletion(self):
        '''Copied from downloadManager. I hope it's ok :)'''
        waitFlag = QEventLoop.WaitForMoreEvents
        while self._running:
            QApplication.processEvents(waitFlag)
