from __future__ import annotations

import json
import os
from enum import Enum
from enum import auto
from typing import TypedDict

from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets

from src import config
from src import fafpath
from src import util
from src.games.mapgenoptions import ComboBoxOption
from src.games.mapgenoptions import RangeOption
from src.games.mapgenoptions import SpinBoxOption
from src.games.mapgenoptionsvalues import GenerationType
from src.games.mapgenoptionsvalues import MapStyle
from src.games.mapgenoptionsvalues import PropStyle
from src.games.mapgenoptionsvalues import ResourceStyle
from src.games.mapgenoptionsvalues import Sentinel
from src.games.mapgenoptionsvalues import TerrainStyle
from src.games.mapgenoptionsvalues import TerrainSymmetry
from src.games.mapgenoptionsvalues import TextureStyle
from src.mapGenerator.mapgenManager import MapGeneratorManager
from src.qt.utils import block_signals

FormClass, BaseClass = util.THEME.loadUiType("games/mapgen.ui")


class MapGenDynamicConfig(TypedDict):
    gen_version: str
    options: dict[str, list[str]]


class OptionsExtractor(QtCore.QObject):
    class State(Enum):
        IDLE = auto()
        EXTRACTING = auto()
        FINISHED = auto()

    options_extracted = QtCore.pyqtSignal(dict)
    error_occured = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal(str)

    def __init__(self, mapgen_manager: MapGeneratorManager, to_extract: list[str]) -> None:
        QtCore.QObject.__init__(self)
        self.state = self.State.IDLE
        self.to_extract = to_extract
        self.extracted_options: dict[str, list[str]] = {}

        self.mapgen_manager = mapgen_manager
        self.process = QtCore.QProcess()
        self.process.finished.connect(self.process_finished)
        self.exe_path = fafpath.get_java_path()

        self.mapgen_path = os.path.join(
            util.MAPGEN_DIR,
            f"MapGenerator_{self.mapgen_manager.currentVersion}.jar",
        )

    def extract_all(self) -> None:
        self.extract_next()

    def extract_next(self) -> None:
        self.state = self.State.EXTRACTING

        if len(self.to_extract) == 0:
            self.state = self.State.FINISHED
            self.options_extracted.emit(self.extracted_options)
            return

        option = self.to_extract.pop(0)
        self.progress.emit(option)
        self.process.start(self.exe_path, ["-jar", self.mapgen_path, option])

    def process_finished(self, code: int, status: QtCore.QProcess.ExitStatus) -> None:
        if code != 0:
            self.state = self.State.FINISHED
            self.error_occured.emit()
            return

        *_, option_name = self.process.arguments()
        out = self.process.readAllStandardOutput()
        self.extracted_options[option_name] = out.data().decode().splitlines()
        if self.to_extract:
            self.extract_next()
        else:
            self.options_extracted.emit(self.extracted_options)
            self.state = self.State.FINISHED

    def set_options_to_extract(self, options: list[str]) -> None:
        self.to_extract = options


class MapGenDialog(FormClass, BaseClass):
    map_generated = QtCore.pyqtSignal(str)

    def __init__(self, mapgen_manager: MapGeneratorManager, *args, **kwargs) -> None:
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)

        util.THEME.stylesheets_reloaded.connect(self.load_stylesheet)

        self.load_stylesheet()

        self.mapgen_manager = mapgen_manager
        self.setWindowTitle(f"Map Generator Options - {self.mapgen_manager.currentVersion}")

        self.generationType.setMinimumWidth(80)
        self.mapStyle.setMinimumWidth(200)

        self.statusBar = QtWidgets.QStatusBar()
        self.statusBar.setSizeGripEnabled(False)
        self.statusBarLayout.addWidget(self.statusBar)

        self.mapNamePlainTextEdit.textChanged.connect(self.user_mapname_changed)
        self.useCustomStyleCheckBox.checkStateChanged.connect(self.on_custom_style)
        self.generationType.currentTextChanged.connect(self.gen_type_changed)
        self.mapSize.valueChanged.connect(self.map_size_changed)
        self.propGenerator.currentTextChanged.connect(self.prop_generator_changed)
        self.resourceGenerator.currentTextChanged.connect(self.resource_generator_changed)
        self.generateMapButton.clicked.connect(self.generate_map)
        self.saveMapGenSettingsButton.clicked.connect(self.save_preferences_and_quit)
        self.resetMapGenSettingsButton.clicked.connect(self.reset_mapgen_prefs)

        self.dynamic_options = self.get_dynamic_options()
        self.options_extractor = OptionsExtractor(self.mapgen_manager, list(self.dynamic_options))
        self.options_extractor.options_extracted.connect(self.on_options_extracted)
        self.options_extractor.error_occured.connect(self.on_options_extraction_error)
        self.options_extractor.progress.connect(
            lambda msg: self.statusBar.showMessage(f"Extracting options: {msg}"),
        )

        self.options_path = os.path.join(util.MAPGEN_DIR, "mapgen_options.json")

    def get_dynamic_options(self) -> dict[str, ComboBoxOption]:
        return {
            "symmetries": ComboBoxOption(
                "terrain-symmetry",
                self.terrainSymmetry,
                Sentinel.RANDOM.value,
                Sentinel.values() + TerrainSymmetry.values(),
            ),
            "styles": ComboBoxOption(
                "style",
                self.mapStyle,
                Sentinel.RANDOM.value,
                Sentinel.values() + MapStyle.values(),
            ),
            "terrain-styles": ComboBoxOption(
                "terrain-style",
                self.terrainStyle,
                Sentinel.RANDOM.value,
                Sentinel.values() + TerrainStyle.values(),
            ),
            "texture-styles": ComboBoxOption(
                "texture-style",
                self.textureStyle,
                Sentinel.RANDOM.value,
                Sentinel.values() + TextureStyle.values(),
            ),
            "resource-styles": ComboBoxOption(
                "resource-style",
                self.resourceGenerator,
                Sentinel.RANDOM.value,
                Sentinel.values() + ResourceStyle.values(),
            ),
            "prop-styles": ComboBoxOption(
                "prop-style",
                self.propGenerator,
                Sentinel.RANDOM.value,
                Sentinel.values() + PropStyle.values(),
            ),
        }

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.options_extractor.state == OptionsExtractor.State.EXTRACTING:
            event.ignore()
            QtWidgets.QMessageBox.warning(
                self,
                "Map Options Extractor",
                "The extractor is still extracting options. Please wait until it is finished.",
            )
        else:
            super().closeEvent(event)

    def on_options_extracted(self, options: dict[str, list[str]]) -> None:
        to_save = {
            "gen_version": self.mapgen_manager.currentVersion,
            "options": options,
        }
        with open(self.options_path, "w") as f:
            json.dump(to_save, f, indent=2)

        self.setWindowTitle(f"Map Generator Options - {self.mapgen_manager.currentVersion}")
        self.setEnabled(True)
        self.set_cmd_options(options)

    def on_options_extraction_error(self) -> None:
        self.setWindowTitle("Map Generator Options")
        self.setEnabled(True)
        try:
            os.unlink(self.options_path)
        except FileNotFoundError:
            pass
        self.set_cmd_options({})

    def _load_dynamic_options(self) -> MapGenDynamicConfig:
        if not os.path.exists(self.options_path):
            return {"gen_version": "-1", "options": {}}
        with open(self.options_path) as f:
            return json.load(f)

    def load_cmd_options(self) -> None:
        dynamic_options = self._load_dynamic_options()
        if dynamic_options["gen_version"] != self.mapgen_manager.currentVersion:
            self.setWindowTitle("Loading Mapgen Options...")
            self.setEnabled(False)
            self.mapgen_manager.checkUpdates()
            self.mapgen_manager.versionController(self.mapgen_manager.latestVersion)
            self.options_extractor.extract_all()
        else:
            self.set_cmd_options(dynamic_options["options"])

    def set_cmd_options(self, dynamic_options: dict[str, list[str]]) -> None:
        self.statusBar.showMessage("")
        for key, mapgen_option in self.dynamic_options.items():
            if key in dynamic_options:
                mapgen_option.set_opts(Sentinel.values() + dynamic_options[key])

        self.cmd_options: list[ComboBoxOption | SpinBoxOption | RangeOption] = [
            ComboBoxOption(
                "visibility",
                self.generationType,
                GenerationType.CASUAL.value,
                GenerationType.values(),
            ),
            *self.dynamic_options.values(),
            SpinBoxOption("spawn-count", self.numberOfSpawns, int, 2),
            SpinBoxOption("num-teams", self.numberOfTeams, int, 2),
            SpinBoxOption("num-to-generate", self.numberOfMaps, int, 1),
            SpinBoxOption("map-size", self.mapSize, float, 5),
            RangeOption(
                "resource-density",
                SpinBoxOption("", self.minResourceDensity, int, 0),
                SpinBoxOption("", self.maxResourceDensity, int, 100),
            ),
            RangeOption(
                "reclaim-density",
                SpinBoxOption("", self.minReclaimDensity, int, 0),
                SpinBoxOption("", self.maxReclaimDensity, int, 100),
            ),
        ]
        self.load_preferences()

    @QtCore.pyqtSlot()
    def user_mapname_changed(self) -> None:
        mapname = self.mapNamePlainTextEdit.toPlainText()
        self.optionsFrame.setEnabled(mapname.strip() == "")

    @QtCore.pyqtSlot(QtCore.Qt.CheckState)
    def on_custom_style(self, state: QtCore.Qt.CheckState) -> None:
        self.customStyleGroupBox.setEnabled(state == QtCore.Qt.CheckState.Checked)
        self.mapStyle.setEnabled(state == QtCore.Qt.CheckState.Unchecked)

    def load_stylesheet(self):
        self.setStyleSheet(util.THEME.readstylesheet("client/client.css"))

    def keyPressEvent(self, event):
        if (
            event.key() == QtCore.Qt.Key.Key_Enter
            or event.key() == QtCore.Qt.Key.Key_Return
        ):
            return
        QtWidgets.QDialog.keyPressEvent(self, event)

    @staticmethod
    def nearest_to_multiple(value: float, to: float) -> float:
        return ((value + to / 2) // to) * to

    @QtCore.pyqtSlot(float)
    def map_size_changed(self, value):
        if (value % 1.25) == 0:
            return
        value = self.nearest_to_multiple(value, 1.25)
        with block_signals(self.mapSize):
            self.mapSize.setValue(value)

    @QtCore.pyqtSlot(str)
    def gen_type_changed(self, text: str) -> None:
        self.casualOptionsFrame.setEnabled(text == GenerationType.CASUAL.value)

    @QtCore.pyqtSlot(str)
    def resource_generator_changed(self, text: str) -> None:
        self.minResourceDensity.setEnabled(text != Sentinel.RANDOM.value)
        self.maxResourceDensity.setEnabled(text != Sentinel.RANDOM.value)

    @QtCore.pyqtSlot(str)
    def prop_generator_changed(self, text: str) -> None:
        self.minReclaimDensity.setEnabled(text != Sentinel.RANDOM.value)
        self.maxReclaimDensity.setEnabled(text != Sentinel.RANDOM.value)

    @QtCore.pyqtSlot()
    def load_preferences(self) -> None:
        for option in self.cmd_options:
            option.load()
        self.useCustomStyleCheckBox.setChecked(
            config.Settings.get(
                "mapGenerator/useCustomStyle",
                type=bool,
                default=False,
            ),
        )
        self.on_custom_style(self.useCustomStyleCheckBox.checkState())

    def save_preferences(self) -> None:
        for option in self.cmd_options:
            option.save()
        config.Settings.set(
            "mapGenerator/useCustomStyle",
            self.useCustomStyleCheckBox.isChecked(),
        )

    @QtCore.pyqtSlot()
    def save_preferences_and_quit(self) -> None:
        self.save_preferences()
        self.done(1)

    @QtCore.pyqtSlot()
    def reset_mapgen_prefs(self) -> None:
        for option in self.cmd_options:
            option.reset()

    @QtCore.pyqtSlot()
    def generate_map(self) -> None:
        if result := self.mapgen_manager.generateMap(args=self.set_arguments()):
            self.map_generated.emit(result)
            self.save_preferences_and_quit()
        else:
            self.save_preferences()

    def set_arguments(self) -> list[str]:
        args = []
        if mapname := self.mapNamePlainTextEdit.toPlainText().strip():
            args.extend(["--map-name", mapname])
        else:
            for option in self.cmd_options:
                if option.name == "map-size":
                    args.append("--map-size")
                    size_px = int(option.value() * 51.2)
                    args.append(str(size_px))
                elif option.active():
                    args.extend(option.as_cmd_arg())
        return args
