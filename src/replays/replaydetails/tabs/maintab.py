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

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtWidgets import QWidget

from src import util
from src.fa.maps import downloadMap
from src.fa.maps import folderForMap
from src.fa.maps import isMapAvailable
from src.fa.maps_.preview import create_large_preview
from src.fa.maps_.preview import largest_preview_scale
from src.fa.maps_.previewdialog import MapPreviewDialog
from src.mapGenerator.mapgenManager import MapGeneratorManager
from src.mapGenerator.mapgenUtils import isGeneratedMap
from src.qt.widgets.clickablelabel import ClickableLabel
from src.replays.replaydetails.replayreader import ReplayParser
from src.replays.replaydetails.utils import PLAYER_COLORS


class ReplayInfoTabUI:
    def setupUi(self, widget: QWidget) -> None:
        self.replayInfo = QTextBrowser()
        self.replayInfo.setText(
            "<h2>No replay loaded</h2>"
            "<p>To load a replay click <b>File</b> menu <b>Load</b> option</p>",
        )
        self.replayInfo.setReadOnly(True)

        self.mapPreview = ClickableLabel()
        self.mapPreview.setMinimumHeight(256)
        self.mapPreview.setMinimumWidth(256)
        self.mapPreview.setMaximumWidth(256)
        self.mapPreview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.mapDescription = QLabel()
        self.mapDescription.setWordWrap(True)
        self.mapDescription.setMaximumWidth(256)
        interaction_flag = Qt.TextInteractionFlag.TextSelectableByMouse
        self.mapDescription.setTextInteractionFlags(interaction_flag)

        map_layout = QHBoxLayout()
        map_layout.setSpacing(6)
        map_layout.addWidget(self.mapPreview)
        map_layout.addWidget(self.mapDescription)

        self.lobbyOptions = QTextBrowser()
        self.lobbyOptions.setReadOnly(True)
        self.lobbyOptions.setVisible(False)

        self.getMapButton = QPushButton("Generate map")
        self.getMapButton.setVisible(False)

        main_layout = QGridLayout(widget)
        main_layout.addWidget(self.replayInfo, 0, 0, 4, 1)
        main_layout.addLayout(map_layout, 0, 1)
        main_layout.addWidget(self.getMapButton, 1, 1)
        main_layout.addWidget(self.lobbyOptions, 2, 1)


class ReplayInfoTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("replay_info_tab")
        self.ui = ReplayInfoTabUI()
        self.ui.setupUi(self)
        self.ui.mapPreview.clicked.connect(self.on_map_clicked)
        self.ui.getMapButton.clicked.connect(self.obtain_map)
        self.replay = ReplayParser()
        self.generator = MapGeneratorManager()

    def initialize(self, replay: ReplayParser) -> None:
        self.replay = replay
        self.ui.replayInfo.setText(self.replay.get_info())
        self.update_lobby_options()
        self.update_map_description()
        self.update_map_pixmap()
        self.update_get_map_button()

    def update_lobby_options(self) -> None:
        self.ui.lobbyOptions.setVisible(True)
        self.ui.lobbyOptions.setText(self.replay.get_settings())

    def update_map_description(self) -> None:
        self.ui.mapDescription.setToolTip(self.replay.map_display_name())
        self.ui.mapDescription.setText(self.replay.luaScenarioInfo["description"].strip())

    def on_map_clicked(self, event: QMouseEvent) -> None:
        event.accept()
        scale = largest_preview_scale(self.screen())
        preview_dialog = MapPreviewDialog(self.map_preview_pixmap(scale=scale))
        preview_dialog.exec()
        preview_dialog.deleteLater()

    def update_map_pixmap(self) -> None:
        pixmap = self.map_preview_pixmap()
        self.ui.mapPreview.setPixmap(pixmap)

    def update_get_map_button(self) -> None:
        map_folder = self.replay.map_folder_name()
        self.ui.getMapButton.setVisible(not isMapAvailable(map_folder))
        text = "Generate map" if isGeneratedMap(map_folder) else "Download map"
        self.ui.getMapButton.setText(text)

    def obtain_map(self) -> None:
        map_folder = self.replay.map_folder_name()
        if isGeneratedMap(map_folder):
            self.generator.generateMap(map_folder)
        else:
            downloadMap(map_folder)
        self.update_map_pixmap()
        self.update_get_map_button()

    def map_preview_pixmap(self, *, scale: int = 1) -> QPixmap:
        nomap = QPixmap(os.path.join(util.COMMON_DIR, "games", "unknown_map.png"))
        folder_path = folderForMap(self.replay.map_folder_name())
        if folder_path is None or not os.path.exists(folder_path):
            return nomap

        armies = {
            army["ArmyName"]: army
            for army in self.replay.army.values()
        }
        for army in armies.values():
            army["hexcolor"] = PLAYER_COLORS[int(army["PlayerColor"]) - 1]
        return create_large_preview(folder_path, armies, scale=scale)
