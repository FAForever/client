import json
import logging
import os
import re
import shlex
from enum import Enum
from enum import auto
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtWidgets import QMessageBox
from semantic_version import Version

from src import config
from src import fafpath
from src import util
from src.api.ApiBase import JsonApiBase
from src.api.models.MapVersion import MapSize
from src.decorators import with_logger
from src.fa.maps import getUserMapsFolder
from src.games.mapgenoptions import CheckableComboBoxOption
from src.games.mapgenoptions import ComboBoxOption
from src.games.mapgenoptions import DoubleSpinBoxOption
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
from src.ui.information_dialog import message_dialog

if TYPE_CHECKING:
    from src.client import ClientWindow

GITHUB_NEXT_PAGE = re.compile(r"(?<=<)([\S]*)(?=>; rel=\"next\")")

FormClass, BaseClass = util.THEME.loadUiType("games/mapgen.ui")


type MapGenDynamicConfig = dict[str, dict[str, list[str]]]


@with_logger
class OptionsExtractor(QtCore.QObject):
    _logger: ClassVar[logging.Logger]

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
        self.process.started.connect(self.process_started)
        self.process.errorOccurred.connect(self.on_error)
        self.exe_path = fafpath.get_java_path()

    def extract_all(self, gen_path: str) -> None:
        self.extracted_options.clear()
        self.mapgen_path = gen_path
        self.extract_next()

    def process_started(self) -> None:
        self.state = self.State.EXTRACTING

    def extract_next(self) -> None:
        if len(self.to_extract) == 0:
            self.state = self.State.FINISHED
            self.options_extracted.emit(self.extracted_options)
            return

        option = self.to_extract.pop(0)
        self.progress.emit(option)
        args = ["-jar", self.mapgen_path, f"--{option}"]
        self._logger.info(
            "Starting MapGenOptionsExtractor with: %s",
            " ".join((self.exe_path, *args)),
        )
        self.process.start(self.exe_path, args)

    def on_error(self, error: QtCore.QProcess.ProcessError) -> None:
        QtWidgets.QMessageBox.critical(
            None,
            "Map Generator Options Extractor",
            f"Map Generator Options Extractor error: {error} ({self.process.errorString()})",
        )
        self._logger.error(
            "Map Generator Options Extractor error: %s (%s)",
            error,
            self.process.errorString(),
        )
        self.state = self.State.FINISHED
        self.error_occured.emit()

    def process_finished(self, code: int, status: QtCore.QProcess.ExitStatus) -> None:
        if code != 0:
            self.on_error(self.process.ProcessError.UnknownError)
            return

        *_, option_name = self.process.arguments()
        out = self.process.readAllStandardOutput()
        self.extracted_options[option_name.removeprefix("--")] = out.data().decode().splitlines()
        if self.to_extract:
            self.extract_next()
        else:
            self.options_extracted.emit(self.extracted_options)
            self.state = self.State.FINISHED

    def set_options_to_extract(self, options: list[str]) -> None:
        self.to_extract = options


class MapGenDialog(FormClass, BaseClass):
    map_generated = QtCore.pyqtSignal(list)

    def __init__(self, parent: ClientWindow, mapgen_manager: MapGeneratorManager) -> None:
        BaseClass.__init__(self, parent)

        self.setupUi(self)

        self.mapgen_manager = mapgen_manager
        self.mapgen_manager.new_available.connect(self.update_version)
        self.setWindowTitle(f"Map Generator Options - {self.mapgen_manager.currentVersion}")

        self.generationType.setMinimumWidth(80)
        self.mapStyle.setMinimumWidth(200)

        self.statusBar = QtWidgets.QStatusBar()
        self.statusBar.setSizeGripEnabled(False)
        self.statusBarLayout.addWidget(self.statusBar)

        self.mapNameEdit.textChanged.connect(self.user_mapname_changed)
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
        self.release_tags = os.path.join(util.MAPGEN_DIR, "release_tags")

        self.api = JsonApiBase()
        self.api.host_config_key = "github_api"
        self.api_reply: QNetworkReply | None = None
        self.releases: set[Version] = set()

        self.buttonFetchVersions.clicked.connect(self.get_all_versions)
        self.buttonSwitchVersion.clicked.connect(self.switch_version)
        self.buttonHelp.clicked.connect(self.run_help)
        self.groupCLI.toggled.connect(self.on_cli_toggled)
        self.checkCLIMapFolder.toggled.connect(self.on_cli_map_folder_toggled)
        self.comboVersion.currentTextChanged.connect(self.on_version_selection_changed)
        self.buttonReloadOptions.clicked.connect(self.reload_cmd_options)

    def get_dynamic_options(self) -> dict[str, CheckableComboBoxOption]:
        return {
            "symmetries": CheckableComboBoxOption(
                "terrain-symmetry",
                self.terrainSymmetry,
                Sentinel.RANDOM.value,
                TerrainSymmetry.values(),
            ),
            "styles": CheckableComboBoxOption(
                "style",
                self.mapStyle,
                Sentinel.RANDOM.value,
                MapStyle.values(),
            ),
            "terrain-styles": CheckableComboBoxOption(
                "terrain-style",
                self.terrainStyle,
                Sentinel.RANDOM.value,
                TerrainStyle.values(),
            ),
            "texture-styles": CheckableComboBoxOption(
                "texture-style",
                self.textureStyle,
                Sentinel.RANDOM.value,
                TextureStyle.values(),
            ),
            "resource-styles": CheckableComboBoxOption(
                "resource-style",
                self.resourceGenerator,
                Sentinel.RANDOM.value,
                ResourceStyle.values(),
            ),
            "prop-styles": CheckableComboBoxOption(
                "prop-style",
                self.propGenerator,
                Sentinel.RANDOM.value,
                PropStyle.values(),
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
        try:
            with open(self.options_path) as f:
                to_save = json.load(f)
            if "gen_version" in to_save:  # XXX: remove backward compatibility
                to_save |= {to_save["gen_version"]: to_save["options"]}
        except FileNotFoundError:
            to_save = {}
        to_save |= {self.mapgen_manager.currentVersion: options}
        with open(self.options_path, "w") as f:
            json.dump(to_save, f, indent=2)

        self.setWindowTitle(f"Map Generator Options - {self.mapgen_manager.currentVersion}")
        self.setEnabled(True)
        self.set_cmd_options(options)

    def on_options_extraction_error(self) -> None:
        self.setWindowTitle("Map Generator Options")
        self.setEnabled(True)
        self.set_cmd_options({})

    def _load_dynamic_options(self) -> MapGenDynamicConfig:
        if not os.path.exists(self.options_path):
            return {}
        with open(self.options_path) as f:
            options = json.load(f)
        if "gen_version" in options:  # XXX: remove backward compatibility
            return options | {options["gen_version"]: options["options"]}
        else:
            return options

    def switch_version(self) -> None:
        version = self.comboVersion.currentText()
        if not version or version == self.mapgen_manager.currentVersion:
            return
        if version == "latest":
            version = self.mapgen_manager.latestVersion
        if self.mapgen_manager.get_generator(version):
            self.mapgen_manager.set_current_version_number(version)
            self.load_cmd_options()
            self.setWindowTitle(f"Map Generator Options - {self.mapgen_manager.currentVersion}")
            self.buttonSwitchVersion.setEnabled(False)

    def on_version_selection_changed(self, text: str) -> None:
        if text == "latest":
            enabled = self.mapgen_manager.currentVersion != self.mapgen_manager.latestVersion
        else:
            enabled = text != self.mapgen_manager.currentVersion
        self.buttonSwitchVersion.setEnabled(enabled)

    def get_all_versions(self) -> None:
        self.buttonFetchVersions.setEnabled(False)
        self.api_reply = self.api.get(
            "/repos/faforever/neroxis-map-generator/releases?per_page=100",
            self.process_releases,  # type: ignore[argument]
            self.on_api_error,
            authorize=False,
        )

    def _get_page(self, full_url: str) -> None:
        path = QtCore.QUrl(full_url).adjusted(
            QtCore.QUrl.UrlFormattingOption.RemoveScheme
            | QtCore.QUrl.UrlFormattingOption.RemoveAuthority,
        ).toString()
        self.api_reply = self.api.get(
            path,
            self.process_releases,  # type: ignore[argument]
            self.on_api_error,
            authorize=False,
        )

    def process_releases(self, message: list[dict[str, Any]]) -> None:
        for release in message:
            for asset in release["assets"]:
                if asset["name"].endswith(".jar"):
                    self.releases.add(Version(release["tag_name"]))
                    break
        assert self.api_reply is not None
        link = self.api_reply.rawHeader("link")
        if not link or (next_url := GITHUB_NEXT_PAGE.search(link.data().decode())) is None:
            self.populate_versions_combo()
            self.buttonFetchVersions.setEnabled(True)
            self.save_release_tags()
            return
        self._get_page(next_url[0])

    def on_api_error(self, reply: QNetworkReply) -> None:
        QMessageBox.critical(
            self, "Error", f"Could not get releases from GitHub API: {reply.error()}",
        )
        self.buttonFetchVersions.setEnabled(True)

    def populate_versions_combo(self) -> None:
        self.comboVersion.clear()
        self.comboVersion.addItem("latest")
        self.comboVersion.addItems(map(str, sorted(self.releases, reverse=True)))
        self.comboVersion.setCurrentText(self.mapgen_manager.currentVersion)

    def update_version(self) -> None:
        if (
            self.comboVersion.currentText() == "latest"
            or QtWidgets.QMessageBox.question(
                self,
                "New version",
                f"A new generator version is available: {self.mapgen_manager.latestVersion}.\n"
                "Do you wish to update?",
            ) == QtWidgets.QMessageBox.StandardButton.Yes
        ):
            self.mapgen_manager.get_generator(self.mapgen_manager.latestVersion)
            self.mapgen_manager.set_current_version_number(self.mapgen_manager.latestVersion)
        self.releases.add(Version(self.mapgen_manager.latestVersion))
        self.comboVersion.insertItem(1, self.mapgen_manager.latestVersion)
        self.save_release_tags()

    def load_release_tags(self) -> None:
        try:
            with open(self.release_tags) as f:
                self.releases = {Version(line) for line in f.readlines()}
        except FileNotFoundError:
            pass
        try:
            self.releases.add(Version(self.mapgen_manager.currentVersion))
        except ValueError:
            pass

    def save_release_tags(self) -> None:
        with open(self.release_tags, "w") as f:
            f.write("\n".join(map(str, sorted(self.releases, reverse=True))))

    def setup(self) -> None:
        self.load_release_tags()
        self.populate_versions_combo()
        self.mapgen_manager.check_updates()
        self.load_cmd_options()
        self.groupCLI.setChecked(config.Settings.get("mapGenerator/cli", False, type=bool))
        self.cliArgsEdit.setText(config.Settings.get("mapGenerator/cliArgs", ""))
        self.checkCLIMapFolder.setChecked(
            config.Settings.get("mapGenerator/cliMapFolder", False, type=bool),
        )
        self.buttonSwitchVersion.setEnabled(False)
        if self.mapgen_manager.latestVersion == self.mapgen_manager.currentVersion:
            self.comboVersion.setCurrentText("latest")

    def load_cmd_options(self) -> None:
        if Version(self.mapgen_manager.currentVersion) < Version("1.12.0"):
            self.set_cmd_options({})
            return
        dynamic_options = self._load_dynamic_options()
        if self.mapgen_manager.currentVersion not in dynamic_options:
            self.mapgen_manager.update_current_if_needed()
            self.setWindowTitle("Loading Mapgen Options...")
            self.setEnabled(False)
            gen_path = self.mapgen_manager.get_generator(self.mapgen_manager.currentVersion)
            self.options_extractor.set_options_to_extract(list(self.dynamic_options))
            self.options_extractor.extract_all(gen_path)
        else:
            self.setWindowTitle(f"Map Generator Options - {self.mapgen_manager.currentVersion}")
            self.set_cmd_options(dynamic_options[self.mapgen_manager.currentVersion])

    def reload_cmd_options(self) -> None:
        self.setEnabled(False)
        self.options_extractor.set_options_to_extract(list(self.dynamic_options))
        gen_path = self.mapgen_manager.get_generator(self.mapgen_manager.currentVersion)
        self.options_extractor.extract_all(gen_path)

    def set_cmd_options(self, dynamic_options: dict[str, list[str]]) -> None:
        self.statusBar.showMessage("")
        for key, mapgen_option in self.dynamic_options.items():
            try:
                mapgen_option.set_opts(dynamic_options[key])
            except KeyError:
                pass

        self.cmd_options = [
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
            DoubleSpinBoxOption("map-size", self.mapSize, float, 5),
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
        self.optionsFrame.setEnabled(self.mapNameEdit.text().strip() == "")

    @QtCore.pyqtSlot(QtCore.Qt.CheckState)
    def on_custom_style(self, state: QtCore.Qt.CheckState) -> None:
        self.customStyleGroupBox.setEnabled(state == QtCore.Qt.CheckState.Checked)
        self.mapStyle.setEnabled(state == QtCore.Qt.CheckState.Unchecked)

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
        config.Settings.set("mapGenerator/cli", self.groupCLI.isChecked())
        config.Settings.set("mapGenerator/cliMapFolder", self.checkCLIMapFolder.isChecked())
        config.Settings.set("mapGenerator/cliArgs", self.cliArgsEdit.text().strip())

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
            message_dialog(self, "Error", "Process output:", self.mapgen_manager.process_stdout)

    def set_arguments(self) -> list[str]:
        if self.groupCLI.isChecked():
            return shlex.split(self.cliArgsEdit.text().strip())
        elif mapname := self.mapNameEdit.text().strip():
            return ["--map-name", mapname]
        else:
            args: list[str] = []
            for option in self.cmd_options:
                if option.name == "map-size":
                    args.append("--map-size")
                    size_px = MapSize.from_side_km(option.value()).width_px
                    args.append(str(size_px))
                elif option.active():
                    args.extend(option.as_cmd_arg())
            return args

    def run_help(self) -> None:
        self.mapgen_manager.run_help()
        message_dialog(self, "Usage", "", self.mapgen_manager.process_stdout)

    def on_cli_toggled(self, on: bool) -> None:
        self.optionsFrame.setEnabled(not on)
        self.mapNameEdit.setEnabled(not on)

    def on_cli_map_folder_toggled(self, on: bool) -> None:
        cli_args = shlex.split(self.cliArgsEdit.text().strip())

        if cli_args and cli_args[0] in ["--folder-path", "--out-path"]:
            if not on:
                cli_args = cli_args[2:]
        elif on:
            cli_args = ["--folder-path", getUserMapsFolder()] + cli_args

        self.cliArgsEdit.setText(shlex.join(cli_args))
