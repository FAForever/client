"""MIT License

Copyright (c) 2020 fafafaf

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
from __future__ import annotations

import json
import os

from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtNetwork
from PyQt6 import QtWidgets

from src import util
from src.config import Settings
from src.mapGenerator.mapgenManager import MapGeneratorManager
from src.qt.utils import center_widget_on_screen
from src.replays.replaydetails.replayreader import Replay
from src.replays.replaydetails.replayreader import ReplayException
from src.replays.replaydetails.replayreader import ReplayParser
from src.replays.replaydetails.tabs.charttab import ChartsTab
from src.replays.replaydetails.tabs.chattab import ChatTab
from src.replays.replaydetails.tabs.gamestats import GameStatsWidget
from src.replays.replaydetails.tabs.heatmap import Heatmap
from src.replays.replaydetails.tabs.maintab import ReplayInfoTab

STYLESHEET = util.THEME.readstylesheet("client/client.css")


class ReplayLoader(QtCore.QThread):
    replayLoaded = QtCore.pyqtSignal(int)
    replayPercentage = QtCore.pyqtSignal(int)
    replayException = QtCore.pyqtSignal(str)

    def __init__(self) -> None:
        QtCore.QObject.__init__(self)
        self.replay = ReplayParser()

    def load_file(self, filename: str) -> None:
        if not filename:
            return

        replay = Replay.from_file(filename)
        self.replay = ReplayParser(replay)
        self.start()

    def load_data(self, data: QtNetwork.QNetworkReply) -> None:
        replay = Replay.from_qreply(data)
        self.replay = ReplayParser(replay)
        self.start()

    def run(self) -> None:
        try:
            self.replay.replayPercentage.connect(self.replayPercentage.emit)
            time = QtCore.QElapsedTimer()
            time.restart()
            self.replay.do_stuff()
            self.replayLoaded.emit(time.elapsed())
            del time
        except ReplayException as e:
            self.replayException.emit(e.args[0])


class ReplayDetailsCard(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs) -> None:
        QtWidgets.QDialog.__init__(self, *args, **kwargs)
        self.setStyleSheet(STYLESHEET)
        window_flags = (
            QtCore.Qt.WindowType.WindowTitleHint
            | QtCore.Qt.WindowType.WindowMaximizeButtonHint
            | QtCore.Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowFlags(window_flags)
        self.setModal(True)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self.setBaseSize(800, 700)
        self.loader = ReplayLoader()
        self.loader.replayLoaded.connect(self.populatePages)
        self.loader.replayException.connect(self.show_replay_exception_msg)

        self.downloader = QtNetwork.QNetworkAccessManager(self)
        self.downloader.finished.connect(self.on_download_finished)

        self.setWindowTitle("Replay Details")

        downloadAction = QtGui.QAction('Download replay', self)
        downloadAction.triggered.connect(self.download_dialog)
        loadAction = QtGui.QAction('Load', self)
        loadAction.triggered.connect(self.select_file)

        self.aboutAction = QtGui.QAction('About', self)
        self.aboutAction.triggered.connect(self.show_about)
        menubar = QtWidgets.QMenuBar()
        filemenu = menubar.addMenu('&File')
        assert filemenu is not None

        filemenu.addAction(loadAction)
        filemenu.addAction(downloadAction)
        filemenu.addSeparator()
        menubar.addAction(self.aboutAction)

        self.replay_info_tab = ReplayInfoTab()
        self.chat_tab = ChatTab()
        self.heatmap_tab = Heatmap()
        self.charts_tab = ChartsTab()
        self.game_stats_tab = GameStatsWidget()

        self.replayTabs = QtWidgets.QTabWidget()
        self.replayTabs.addTab(self.replay_info_tab, "Info")
        self.replayTabs.addTab(self.chat_tab, "Chat")
        self.replayTabs.addTab(self.heatmap_tab, "Heatmap")
        self.replayTabs.addTab(self.charts_tab, "Graph")
        self.replayTabs.addTab(self.game_stats_tab, "Game Stats")

        self.loadingBar = QtWidgets.QProgressBar()
        self.loadingBar.hide()
        self.statusBar = QtWidgets.QStatusBar()
        self.statusBar.setSizeGripEnabled(False)
        self.statusBar.addWidget(self.loadingBar, 1)

        db_path = os.path.join(util.COMMON_DIR, "unitdb", "unitdb.json")
        with open(db_path) as file:
            self.unitsdb = json.loads(file.read())

        self._layout.addWidget(self.replayTabs)
        self._layout.addWidget(self.statusBar)
        self._layout.setMenuBar(menubar)
        self.setLayout(self._layout)
        self.resize(1024, 768)
        self.generator = MapGeneratorManager()

        self.tab_history = set()
        self.replayTabs.currentChanged.connect(self.on_tab_changed)

        self.download_timer = QtCore.QElapsedTimer()
        self.download_time = 0
        self._restore_geometry_from_settings()

    def _restore_geometry_from_settings(self) -> None:
        with Settings.group("replaycard") as settings:
            self.restoreGeometry(settings.value("geometry", self.saveGeometry()))
            center_widget_on_screen(self)

    def _save_geometry_to_settings(self) -> None:
        with Settings.group("replaycard") as settings:
            settings.setValue("geometry", self.saveGeometry())

    def closeEvent(self, event: QtGui.QCloseEvent | None) -> None:
        self._save_geometry_to_settings()
        super().closeEvent(event)

    def on_tab_changed(self, index: int) -> None:
        if index in self.tab_history:
            return

        self.tab_history.add(index)
        widget = self.replayTabs.widget(index)
        assert isinstance(widget, (ReplayInfoTab, ChatTab, ChartsTab, GameStatsWidget, Heatmap))
        widget.initialize(self.loader.replay)

    def show_replay_exception_msg(self, msg: str) -> None:
        self.statusBar.showMessage("")
        msg = f"Can't parse this replay.<br/><br/>Error message:<br/><b>{msg}</b>"
        QtWidgets.QMessageBox.warning(self, "Error", msg)

    def download_dialog(self) -> None:

        def start_it():
            try:
                self.download_by_id(int(replayInput.text()))
                dialog.close()
            except ValueError:
                QtWidgets.QMessageBox.warning(self, "Error", "Replay id must be number")
                replayInput.clear()

        dialog = QtWidgets.QDialog(
            None,
            QtCore.Qt.WindowType.WindowTitleHint
            | QtCore.Qt.WindowType.WindowSystemMenuHint
            | QtCore.Qt.WindowType.WindowMinimizeButtonHint
            | QtCore.Qt.WindowType.WindowMaximizeButtonHint
            | QtCore.Qt.WindowType.WindowCloseButtonHint,
        )
        dialog.setWindowTitle("Download FAF replay")
        dialogLayout = QtWidgets.QVBoxLayout()
        replayInput = QtWidgets.QLineEdit()
        replayInput.setPlaceholderText("replay id")
        replayInput.returnPressed.connect(start_it)
        connectButton = QtWidgets.QToolButton()
        connectButton.setText("Download")
        connectButton.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
        connectButton.clicked.connect(start_it)
        dialogLayout.addWidget(QtWidgets.QLabel("Please enter the replay id"))
        dialogLayout.addWidget(replayInput)
        dialogLayout.addWidget(connectButton, 0)
        dialog.setLayout(dialogLayout)
        dialog.exec()

    def download_by_id(self, id: int) -> None:
        host = Settings.get("replay_vault/host")
        url = QtCore.QUrl(host).resolved(QtCore.QUrl(str(id)))
        self.download_by_url(url)

    def download_by_url(self, qurl: QtCore.QUrl) -> None:
        self.statusBar.showMessage("Downloading replay...")
        self.download_timer.restart()
        self.download_time = 0
        self.downloader.get(QtNetwork.QNetworkRequest(qurl))

    def on_download_finished(self, reply: QtNetwork.QNetworkReply) -> None:
        self.download_time = self.download_timer.elapsed()
        if (
            reply.error() == reply.NetworkError.NoError
            and reply.header(QtNetwork.QNetworkRequest.KnownHeaders.ContentLengthHeader) != 0
        ):
            self.replayTabs.setCurrentIndex(0)
            self.statusBar.showMessage("Parsing the replay file..")
            self.loader.load_data(reply)
            self.setWindowTitle(reply.url().url())
        else:
            self.statusBar.showMessage("Download failed")
            QtWidgets.QMessageBox.warning(self, 'Error', 'Can\'t download that replay')
        reply.deleteLater()

    def show_about(self) -> None:
        about = QtWidgets.QDialog(None, QtCore.Qt.WindowType.Widget)
        about.setWindowTitle("About")
        aboutText = (
            """
                <h3>Based on Synced Live Replay server</h3>
                <h5>by PattogoTehen in 2013</h5>
                <p>
                    More info on faf forum: <a href="http://forums.faforever.com/viewtopic.php?f=41&t=5774">http://forums.faforever.com/viewtopic.php?f=41&t=5774</a> <br/>
                    Source available on GitHub: <a href="https://github.com/fafafaf/livereplayserver">https://github.com/fafafaf/livereplayserver</a> <br/>
                    Online replay parser: <a href="https://fafafaf.github.io">https://fafafaf.github.io<a/>
                </p>
                <p>
                    Huge thanks to Aulex and TA4Life for testing, and Domino for lua support
                </p>
            """  # noqa: E501
        )
        aboutLabel = QtWidgets.QLabel(aboutText)
        aboutLabel.setWordWrap(True)
        aboutLabel.setOpenExternalLinks(True)
        aboutLabel.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
            | QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse,
        )
        aboutLayout = QtWidgets.QVBoxLayout()
        aboutLayout.addWidget(aboutLabel)
        about.setLayout(aboutLayout)
        about.exec()

    @QtCore.pyqtSlot(int)
    def populatePages(self, ms: int) -> None:
        self.statusBar.showMessage(f"Download: {self.download_time} ms; Parse: {ms} ms")
        self.tab_history.clear()
        self.on_tab_changed(0)

    @QtCore.pyqtSlot()
    def select_file(self) -> None:
        file, _ = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select FA replay",
            os.path.join(util.APPDATA_DIR, "replays"),
            "*.fafreplay;;*.SCFAReplay",
        )
        if file:
            self.replay(file)

    def replay(self, path: str) -> None:
        self.replayTabs.setCurrentIndex(0)
        self.setWindowTitle(os.path.basename(str(path)))
        self.download_time = 0
        self.statusBar.showMessage("Parsing the replay file..")
        self.loader.load_file(path)
