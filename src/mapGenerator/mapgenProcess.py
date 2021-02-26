from decorators import with_logger
from PyQt5.QtCore import QProcess, QProcessEnvironment, QEventLoop, Qt
from PyQt5.QtWidgets import QMessageBox, QApplication, QProgressDialog
import os
import fafpath
from util import getJavaPath
import re
from . import mapgenUtils
import logging
from config import setup_file_handler

logger = logging.getLogger(__name__)
#Separate log file for map generator
generatorLogger = logging.getLogger(__name__)
generatorLogger.propagate = False
generatorLogger.addHandler(setup_file_handler('map_generator.log'))

class MapGeneratorProcess(object):
    def __init__(self, gen_path, out_path, args):
        self._progress = QProgressDialog()
        self._progress.setWindowTitle("Generating map, please wait...")
        self._progress.setCancelButtonText("Cancel")
        self._progress.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        self._progress.setAutoReset(False)
        self._progress.setModal(1)
        self._progress.setMinimum(0)
        self._progress.setMaximum(30)
        self._progress.canceled.connect(self.close)
        self.progressCounter = 1

        self.map_generator_process = QProcess()
        self.map_generator_process.setWorkingDirectory(out_path)
        self.map_generator_process.readyReadStandardOutput.connect(self.on_log_ready)
        self.map_generator_process.readyReadStandardError.connect(self.on_error_ready)
        self.map_generator_process.finished.connect(self.on_exit)
        self.map_name = None

        self.java_path = getJavaPath()
        args = ["-jar", gen_path] + args

        logger.info("Starting map generator with {} {}".format(self.java_path, " ".join(args)))
        generatorLogger.info(">>> --------------------------- MapGenerator Launch")

        self.map_generator_process.start(self.java_path, args)

        if not self.map_generator_process.waitForStarted(5000):
            logger.error("error starting the map generator process")
            QMessageBox.critical(None, "Map generator error", "The map generator did not start.")
        else:
            self._progress.show()
            self._running = True
            self.waitForCompletion()

    @property
    def mapname(self):
        return str(self.map_name)
    
    def on_log_ready(self):
        data = self.map_generator_process.readAllStandardOutput().data().decode('utf8').split('\n')
        for line in data:
            if re.match(mapgenUtils.generatedMapPattern, line) and self.map_name is None:
                self.map_name = line.strip()
            if line != '':
                generatorLogger.info(line.strip())
            # Kinda fake progress bar. Better than nothing :)
            if len(line) > 4:
                self._progress.setLabelText(line[:25] + "...")
                self.progressCounter += 1
                self._progress.setValue(self.progressCounter)

    def on_error_ready(self):
        for line in str(self.map_generator_process.readAllStandardError()).splitlines():
            logger.debug("MapGenERROR: " + line)

    def on_exit(self, code, status):
        self._progress.reset()
        self._running = False
        generatorLogger.info("<<< --------------------------- MapGenerator Shutdown")

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
