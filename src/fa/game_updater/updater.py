"""
This is the FORGED ALLIANCE updater.

It ensures, through communication with faforever.com, that Forged Alliance
is properly updated, patched, and all required files for a given mod are
installed

@author thygrrr
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import QEventLoop
from PyQt6.QtCore import QObject
from PyQt6.QtCore import QThread
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QDialog

from src import util
from src.downloadManager import FileDownload
from src.fa.game_updater.misc import ProgressInfo
from src.fa.game_updater.misc import UpdaterResult
from src.fa.game_updater.misc import clear_log
from src.fa.game_updater.misc import failure_dialog
from src.fa.game_updater.misc import log
from src.fa.game_updater.misc import timestamp
from src.fa.game_updater.worker import UpdaterWorker

logger = logging.getLogger(__name__)


FormClass, BaseClass = util.THEME.loadUiType("fa/updater/updater.ui")


class UpdaterProgressDialog(FormClass, BaseClass):
    aborted = pyqtSignal()

    def __init__(self, parent: QObject | None, silent: bool = False) -> None:
        BaseClass.__init__(self, parent)
        self.setupUi(self)
        self.setModal(True)
        self.logPlainTextEdit.setLineWrapMode(self.logPlainTextEdit.LineWrapMode.NoWrap)
        self.logFrame.setVisible(False)
        self.adjustSize()
        self.watches = []

        if silent:
            self.abortButton.hide()

        self.rejected.connect(self.abort)
        self.abortButton.clicked.connect(self.reject)
        self.detailsButton.clicked.connect(self.change_details_visibility)
        self.load_stylesheet()

    def load_stylesheet(self):
        self.setStyleSheet(util.THEME.readstylesheet("client/client.css"))

    def change_details_visibility(self) -> None:
        visible = self.logFrame.isVisible()
        self.logFrame.setVisible(not visible)
        self.adjustSize()

    def abort(self) -> None:
        self.aborted.emit()

    @pyqtSlot(str)
    def append_log(self, text: str) -> None:
        self.logPlainTextEdit.appendPlainText(text)

    def replace_last_log_line(self, text: str) -> None:
        self.logPlainTextEdit.moveCursor(
            QTextCursor.MoveOperation.StartOfLine,
            QTextCursor.MoveMode.KeepAnchor,
        )
        self.logPlainTextEdit.textCursor().removeSelectedText()
        self.logPlainTextEdit.insertPlainText(text)

    @pyqtSlot(QObject)
    def add_watch(self, watch: QObject) -> None:
        self.watches.append(watch)
        watch.finished.connect(self.watch_finished)

    @pyqtSlot()
    def watch_finished(self) -> None:
        for watch in self.watches:
            if not watch.isFinished():
                return
        # equivalent to self.accept(), but clearer
        self.done(QDialog.DialogCode.Accepted)

    def on_processed_mod_changed(self, info: ProgressInfo) -> None:
        text = f"Updating {info.description.upper()}... ({info.progress}/{info.total})"
        self.currentModLabel.setText(text)
        self.hashProgress.setValue(0)
        self.modProgress.setValue(0)
        self.extrasProgress.setValue(0)

    def on_movies_progress(self, info: ProgressInfo) -> None:
        self.extrasProgress.setMaximum(info.total)
        self.extrasProgress.setValue(info.progress)
        self.append_log(f"Checking for movies and sounds: {info.description}")

    def on_hash_progress(self, info: ProgressInfo) -> None:
        self.hashProgress.setMaximum(info.total)
        self.hashProgress.setValue(info.progress)
        self.append_log(f"Calculating md5: {info.description}")

    def on_game_progress(self, info: ProgressInfo) -> None:
        self.gameProgress.setMaximum(info.total)
        self.gameProgress.setValue(info.progress)
        self.append_log(f"Checking/copying game file: {info.description}")

    def on_mod_progress(self, info: ProgressInfo) -> None:
        if info.total == 0:
            self.modProgress.setMaximum(1)
            self.modProgress.setValue(1)
            self.append_log("Everything is up to date.")
        else:
            self.append_log(f"Updating file: {info.description}")
            self.modProgress.setMaximum(info.total)
            self.modProgress.setValue(info.progress)

    def on_download_progress(self, dler: FileDownload) -> None:
        if dler.bytes_total == 0:
            return

        total = dler.bytes_total
        ready = dler.bytes_progress

        total_mb = round(total / (1024 ** 2), 2)
        ready_mb = round(ready / (1024 ** 2), 2)

        def construct_bar(blockchar: str = "=", fillchar: str = " ") -> str:
            num_blocks = round(20 * ready / total)
            empty_blocks = 20 - num_blocks
            return f"[{blockchar * num_blocks}{fillchar * empty_blocks}]"

        bar = construct_bar()
        percent_text = f"{100 * ready / total:.1f}%"
        text = f"{bar} {percent_text} ({ready_mb} MB / {total_mb} MB)"
        self.replace_last_log_line(text)

    def on_download_finished(self, dler: FileDownload) -> None:
        self.append_log("Finished downloading.")

    def on_download_started(self, dler: FileDownload) -> None:
        self.append_log(f"Downloading file from {dler.addr}\n")


class Updater(QObject):
    """
    This is the class that does the actual installation work.
    """

    finished = pyqtSignal()

    def __init__(
            self,
            featured_mod: str,
            version: int | None = None,
            modversions: dict[str, int] | None = None,
            silent: bool = False,
    ) -> None:
        """
        Constructor
        """
        super().__init__()

        self.progress = UpdaterProgressDialog(None, silent)
        self.progress.aborted.connect(self.abort)

        self.worker_thread = QThread()
        self.worker = UpdaterWorker(featured_mod, version, modversions, silent)
        self.worker.moveToThread(self.worker_thread)

        self.worker.done.connect(self.on_update_done)
        self.worker.current_mod.connect(self.progress.on_processed_mod_changed)
        self.worker.hash_progress.connect(self.progress.on_hash_progress)
        self.worker.extras_progress.connect(self.progress.on_movies_progress)
        self.worker.game_progress.connect(self.progress.on_game_progress)
        self.worker.mod_progress.connect(self.progress.on_mod_progress)
        self.worker.download_progress.connect(self.progress.on_download_progress)
        self.worker.download_finished.connect(self.progress.on_download_finished)
        self.worker.download_started.connect(self.progress.on_download_started)
        self.worker_thread.started.connect(self.worker.do_update)
        self.result = UpdaterResult.NONE

    def run(self) -> UpdaterResult:
        clear_log()
        log(f"Update started at {timestamp()}", logger)
        log(f"Using appdata: {util.APPDATA_DIR}", logger)

        self.progress.show()
        self.worker_thread.start()

        loop = QEventLoop()
        self.worker_thread.finished.connect(loop.quit)
        loop.exec()

        self.progress.accept()
        log(f"Update finished at {timestamp()}", logger)
        return self.result

    def on_update_done(self, result: UpdaterResult) -> None:
        self.result = result
        self.handle_result_if_needed(result)
        self.stop_thread()

    def handle_result_if_needed(self, result: UpdaterResult) -> None:
        # Integrated handlers for the various things that could go wrong
        if result == UpdaterResult.CANCEL:
            pass  # The user knows damn well what happened here.
        elif result == UpdaterResult.FAILURE:
            failure_dialog()

    def abort(self) -> None:
        self.worker.abort()

    def stop_thread(self) -> None:
        self.worker_thread.quit()
        self.worker_thread.wait(1000)

    @property
    def game_version(self) -> int:
        return self.worker.version or -1
