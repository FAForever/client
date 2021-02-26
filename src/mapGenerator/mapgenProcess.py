from decorators import with_logger
from PyQt5.QtCore import QProcess, QProcessEnvironment, QEventLoop, Qt
from PyQt5.QtWidgets import QMessageBox, QApplication, QProgressDialog
import os
import fafpath
from util import getJavaPath

@with_logger
class MapGeneratorProcess(object):
    def __init__(self, gen_path, out_path, seed, version, mapName):
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
        self.map_generator_process.readyReadStandardOutput.connect(self.on_log_ready)
        self.map_generator_process.readyReadStandardError.connect(self.on_error_ready)
        self.map_generator_process.finished.connect(self.on_exit)

        self.java_path = getJavaPath()
        args = ["-jar", gen_path, out_path, seed, version, mapName]

        self._logger.debug("running map generator with {} {}".format(self.java_path, " ".join(args)))

        self.map_generator_process.start(self.java_path, args)

        if not self.map_generator_process.waitForStarted(5000):
            self._logger.error("error starting the map generator process")
            QMessageBox.critical(None, "Map generator error", "The map generator did not start.")
        else:
            self._progress.show()
            self._running = True
            self.waitForCompletion()

    def on_log_ready(self):
        rawLine = self.map_generator_process.readAllStandardOutput().data().decode('utf8').split('\n', 1)[0]

        # Kinda fake progress bar. Better than nothing :)
        if len(rawLine) > 4:
            self._progress.setLabelText(rawLine[:25] + "...")
            self.progressCounter += 1
            self._progress.setValue(self.progressCounter)

    def on_error_ready(self):
        for line in str(self.map_generator_process.readAllStandardError()).splitlines():
            self._logger.debug("MapGenERROR: " + line)

    def on_exit(self, code, status):
        self._progress.reset()
        self._running = False

    def close(self):
        if self.map_generator_process.state() == QProcess.Running:
            self._logger.info("Waiting for map generator process shutdown")
            if not self.map_generator_process.waitForFinished(300):
                if self.map_generator_process.state() == QProcess.Running:
                    self._logger.error("Terminating map generator process")
                    self.map_generator_process.terminate()
                    if not self.map_generator_process.waitForFinished(300):
                        self._logger.error("Killing map generator process")
                        self.map_generator_process.kill()

    def waitForCompletion(self):
        '''Copied from downloadManager. I hope it's ok :)'''
        waitFlag = QEventLoop.WaitForMoreEvents
        while self._running:
            QApplication.processEvents(waitFlag) 
