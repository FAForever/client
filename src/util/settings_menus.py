from __future__ import annotations

import os
import textwrap
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QButtonGroup
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QDialogButtonBox
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QRadioButton
from PyQt6.QtWidgets import QSpinBox
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src import util
from src.config import Settings
from src.fa.path import validate_game_path
from src.fa.path import validate_path
from src.vaults.modvault.utils import setModFolder

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow


class CacheSettingsUI:
    def setupUi(self, widget: QWidget) -> None:
        main_layout = QVBoxLayout(widget)

        game_files_group = QGroupBox("Game Files Cache")
        game_files_layout = QVBoxLayout()

        self.gameFilesButtonGroup = QButtonGroup(widget)

        self.gameNeverRadio = QRadioButton("Don't keep")
        self.gameForeverRadio = QRadioButton("Keep forever")
        self.gameSessionRadio = QRadioButton("Keep in current session")
        self.gameCustomRadio = QRadioButton("Keep cache for:")

        self.gameFilesButtonGroup.addButton(self.gameNeverRadio, 1)
        self.gameFilesButtonGroup.addButton(self.gameForeverRadio, 2)
        self.gameFilesButtonGroup.addButton(self.gameSessionRadio, 3)
        self.gameFilesButtonGroup.addButton(self.gameCustomRadio, 4)

        self.gameNeverRadio.setChecked(True)

        game_files_layout.addWidget(self.gameNeverRadio)
        game_files_layout.addWidget(self.gameForeverRadio)
        game_files_layout.addWidget(self.gameSessionRadio)

        custom_game_layout = QHBoxLayout()
        custom_game_layout.addWidget(self.gameCustomRadio)
        self.gameDaysSpinbox = QSpinBox()
        self.gameDaysSpinbox.setMinimum(1)
        self.gameDaysSpinbox.setMaximum(9999)
        self.gameDaysSpinbox.setValue(30)
        self.gameDaysSpinbox.setSuffix(" days")
        self.gameDaysSpinbox.setEnabled(False)
        custom_game_layout.addWidget(self.gameDaysSpinbox)
        custom_game_layout.addStretch()

        game_files_layout.addLayout(custom_game_layout)

        game_header_layout = QHBoxLayout()
        game_header_layout.addStretch()
        self.showGameCacheFolder = QPushButton("Show Folder")
        game_header_layout.addWidget(self.showGameCacheFolder)
        game_files_layout.addLayout(game_header_layout)

        game_files_group.setLayout(game_files_layout)

        ice_adapter_group = QGroupBox("ICE Adapter Cache")
        ice_adapter_group.setToolTip("Previously downloaded old versions of ICE Adapters")
        ice_adapter_layout = QVBoxLayout()

        self.iceAdapterButtonGroup = QButtonGroup(widget)

        self.iceForeverRadio = QRadioButton("Keep unused forever")
        self.iceCustomRadio = QRadioButton("Keep unused for:")

        self.iceAdapterButtonGroup.addButton(self.iceForeverRadio, 1)
        self.iceAdapterButtonGroup.addButton(self.iceCustomRadio, 2)

        self.iceForeverRadio.setChecked(True)

        ice_adapter_layout.addWidget(self.iceForeverRadio)

        custom_ice_layout = QHBoxLayout()
        custom_ice_layout.addWidget(self.iceCustomRadio)
        self.iceDaysSpinbox = QSpinBox()
        self.iceDaysSpinbox.setMinimum(0)
        self.iceDaysSpinbox.setMaximum(9999)
        self.iceDaysSpinbox.setValue(30)
        self.iceDaysSpinbox.setSuffix(" days")
        self.iceDaysSpinbox.setEnabled(False)
        custom_ice_layout.addWidget(self.iceDaysSpinbox)
        custom_ice_layout.addStretch()

        ice_adapter_layout.addLayout(custom_ice_layout)

        ice_header_layout = QHBoxLayout()
        ice_header_layout.addStretch()
        self.showIceAdapterFolder = QPushButton("Show Folder")
        ice_header_layout.addWidget(self.showIceAdapterFolder)
        ice_adapter_layout.addLayout(ice_header_layout)

        ice_adapter_group.setLayout(ice_adapter_layout)

        map_gen_group = QGroupBox("Map Generator Cache")
        map_gen_group.setToolTip("Previously downloaded old versions of Map Generator")
        map_gen_layout = QVBoxLayout()

        self.mapGenButtonGroup = QButtonGroup(widget)

        self.mapgenForeverRadio = QRadioButton("Keep unused forever")
        self.mapgenCustomRadio = QRadioButton("Keep unused for:")

        self.mapGenButtonGroup.addButton(self.mapgenForeverRadio, 1)
        self.mapGenButtonGroup.addButton(self.mapgenCustomRadio, 2)

        self.mapgenForeverRadio.setChecked(True)

        map_gen_layout.addWidget(self.mapgenForeverRadio)

        custom_mapgen_layout = QHBoxLayout()
        custom_mapgen_layout.addWidget(self.mapgenCustomRadio)
        self.mapgenDaysSpinbox = QSpinBox()
        self.mapgenDaysSpinbox.setMinimum(0)
        self.mapgenDaysSpinbox.setMaximum(9999)
        self.mapgenDaysSpinbox.setValue(30)
        self.mapgenDaysSpinbox.setSuffix(" days")
        self.mapgenDaysSpinbox.setEnabled(False)
        custom_mapgen_layout.addWidget(self.mapgenDaysSpinbox)
        custom_mapgen_layout.addStretch()

        map_gen_layout.addLayout(custom_mapgen_layout)

        mapgen_header_layout = QHBoxLayout()
        mapgen_header_layout.addStretch()
        self.showMapGenFolder = QPushButton("Show Folder")
        mapgen_header_layout.addWidget(self.showMapGenFolder)
        map_gen_layout.addLayout(mapgen_header_layout)

        map_gen_group.setLayout(map_gen_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.okButton = QPushButton("OK")
        self.cancelButton = QPushButton("Cancel")
        self.applyButton = QPushButton("Apply")

        buttons_layout.addWidget(self.okButton)
        buttons_layout.addWidget(self.cancelButton)
        buttons_layout.addWidget(self.applyButton)

        main_layout.addWidget(game_files_group)
        main_layout.addWidget(ice_adapter_group)
        main_layout.addWidget(map_gen_group)
        main_layout.addStretch()
        main_layout.addLayout(buttons_layout)


class CacheSetting(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cache Settings")
        self.setMinimumWidth(500)
        self.ui = CacheSettingsUI()
        self.ui.setupUi(self)

        self.ui.gameCustomRadio.toggled.connect(self.ui.gameDaysSpinbox.setEnabled)
        self.ui.iceCustomRadio.toggled.connect(self.ui.iceDaysSpinbox.setEnabled)
        self.ui.mapgenCustomRadio.toggled.connect(self.ui.mapgenDaysSpinbox.setEnabled)

        game_cache_folder = os.path.join(util.CACHE_DIR, "featured_mod")
        self.ui.showGameCacheFolder.clicked.connect(
            lambda: util.showDirInFileBrowser(game_cache_folder),
        )
        self.ui.showIceAdapterFolder.clicked.connect(
            lambda: util.showDirInFileBrowser(util.ICE_ADAPTER_DIR),
        )
        self.ui.showMapGenFolder.clicked.connect(lambda: util.showDirInFileBrowser(util.MAPGEN_DIR))

        self.ui.okButton.clicked.connect(self.save_settings_and_quit)
        self.ui.cancelButton.clicked.connect(self.reject)
        self.ui.applyButton.clicked.connect(self.save_settings)

    def load_settings(self) -> None:
        game_duration = Settings.get("cache/store_duration", default=30, type=int)

        if game_duration == -1:
            self.ui.gameNeverRadio.setChecked(True)
        elif game_duration == 0:
            self.ui.gameSessionRadio.setChecked(True)
        elif game_duration == 99999:
            self.ui.gameForeverRadio.setChecked(True)
        else:
            self.ui.gameCustomRadio.setChecked(True)
            self.ui.gameDaysSpinbox.setValue(game_duration)

        ice_duration = Settings.get("iceadapter/store_duration", default=30, type=int)
        if ice_duration == 99999:
            self.ui.iceForeverRadio.setChecked(True)
        else:
            self.ui.iceCustomRadio.setChecked(True)
            self.ui.iceDaysSpinbox.setValue(ice_duration)

        mapgen_duration = Settings.get("mapGenerator/store_duration", default=30, type=int)
        if mapgen_duration == 99999:
            self.ui.mapgenForeverRadio.setChecked(True)
        else:
            self.ui.mapgenCustomRadio.setChecked(True)
            self.ui.mapgenDaysSpinbox.setValue(mapgen_duration)

    def save_settings(self) -> None:
        for button in self.ui.gameFilesButtonGroup.buttons():
            if not button.isChecked():
                continue
            match button:
                case self.ui.gameNeverRadio:
                    Settings.set("cache/store_duration", -1)
                case self.ui.gameForeverRadio:
                    Settings.set("cache/store_duration", 99999)
                case self.ui.gameSessionRadio:
                    Settings.set("cache/store_duration", 0)
                case self.ui.gameCustomRadio:
                    Settings.set("cache/store_duration", self.ui.gameDaysSpinbox.value())
                case _:
                    pass

        for button in self.ui.iceAdapterButtonGroup.buttons():
            if not button.isChecked():
                continue
            if button is self.ui.iceForeverRadio:
                Settings.set("iceadapter/store_duration", 99999)
            else:
                Settings.set("iceadapter/store_duration", self.ui.iceDaysSpinbox.value())

        for button in self.ui.mapGenButtonGroup.buttons():
            if not button.isChecked():
                continue
            if button is self.ui.mapgenForeverRadio:
                Settings.set("mapGenerator/store_duration", 99999)
            else:
                Settings.set("mapGenerator/store_duration", self.ui.mapgenDaysSpinbox.value())

    def save_settings_and_quit(self) -> None:
        self.save_settings()
        self.accept()


def show_cache_settings(client: ClientWindow) -> None:
    dialog = CacheSetting(client)
    dialog.load_settings()
    dialog.exec()


class GameSettingsUI:
    def setupUi(self, widget: QWidget) -> None:
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        game_path_group = QGroupBox("Game Location")
        game_path_group.setObjectName("vaultSettingsGroupBox")
        game_path_layout = QHBoxLayout(game_path_group)

        self.gamePathInput = QLineEdit()
        self.browseGameButton = QPushButton("Browse")

        game_path_layout.addWidget(self.gamePathInput)
        game_path_layout.addWidget(self.browseGameButton)

        vault_path_group = QGroupBox("Maps and Mods Location")
        vault_path_group.setObjectName("vaultSettingsGroupBox")
        vault_path_layout = QHBoxLayout(vault_path_group)

        self.vaultPathInput = QLineEdit()
        self.browseVaultButton = QPushButton("Browse")

        vault_path_layout.addWidget(self.vaultPathInput)
        vault_path_layout.addWidget(self.browseVaultButton)

        misc_settings_group = QGroupBox("Other")
        misc_settings_group.setObjectName("vaultSettingsGroupBox")
        misc_settings_layout = QVBoxLayout(misc_settings_group)

        self.gameLogsCheckBox = QCheckBox("Save Game Logs")
        self.runReplaysSeparatelyCheckBox = QCheckBox("Run replay as its own process")
        tooltip = textwrap.dedent(
            """\
            Allows to run replays alongside running game process.
            All necessary game files will be downloaded into a separate
            dedicated directory, which will require additional disk space.
            """,
        )
        self.runReplaysSeparatelyCheckBox.setToolTip(tooltip)
        misc_settings_layout.addWidget(self.gameLogsCheckBox)
        misc_settings_layout.addWidget(self.runReplaysSeparatelyCheckBox)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        )

        layout.addWidget(game_path_group)
        layout.addWidget(vault_path_group)
        layout.addWidget(misc_settings_group)
        layout.addStretch()
        layout.addWidget(self.buttons)


class GameSettings(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Forged Alliance Settings")
        self.ui = GameSettingsUI()
        self.ui.setupUi(self)
        self.setMinimumWidth(600)
        self.ui.buttons.accepted.connect(self.save_settings)
        self.ui.buttons.rejected.connect(self.reject)

    def setup(self) -> None:
        self.ui.gamePathInput.setText(Settings.get("ForgedAlliance/app/path", ""))
        self.ui.vaultPathInput.setText(util.VAULTS_BASE_DIR)
        self.ui.gameLogsCheckBox.setChecked(Settings.get("game/logs", True, type=bool))
        self.ui.runReplaysSeparatelyCheckBox.setChecked(
            Settings.get("game/replay_process", True, type=bool),
        )
        self.ui.browseGameButton.clicked.connect(
            lambda: self.browse_directory(self.ui.gamePathInput),
        )
        self.ui.browseVaultButton.clicked.connect(
            lambda: self.browse_directory(self.ui.vaultPathInput),
        )

    def browse_directory(self, line_edit: QLineEdit) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            line_edit.text() or "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if directory:
            line_edit.setText(directory)

    def save_settings(self) -> None:
        game_path = self.ui.gamePathInput.text()
        vault_path = self.ui.vaultPathInput.text()
        suggestion = """{path_type} Path is invalid. Make sure:
            1. It exists
            2. It doesn't contain any non-ASCII characters
            3. It doesn't end with slash ('/') or ('\\')

        {path}
        """
        if not validate_game_path(game_path):
            QMessageBox.critical(
                self,
                "Invalid Path",
                suggestion.format(path_type="Game", path=game_path),
            )
            return
        if not validate_path(vault_path):
            QMessageBox.critical(
                self,
                "Invalid Path",
                suggestion.format(path_type="Vault", path=vault_path),
            )
            return
        Settings.set("ForgedAlliance/app/path", game_path)
        Settings.set("game/logs", self.ui.gameLogsCheckBox.isChecked())
        Settings.set("game/replay_process", self.ui.runReplaysSeparatelyCheckBox.isChecked())
        if vault_path != util.VAULTS_BASE_DIR:
            # TODO: change without restart (or make sure that restart is not needed)
            util.change_vaults_base_dir(vault_path)
            setModFolder()
            QMessageBox.information(
                self,
                "Restart",
                (
                    "Vault path has been changed. Please restart the client in order to properly "
                    "load Maps and Mods from the new Vault Location"
                ),
            )
        self.accept()


def show_game_settings(client: ClientWindow) -> None:
    dialog = GameSettings(client)
    dialog.setup()
    dialog.exec()
    dialog.deleteLater()
