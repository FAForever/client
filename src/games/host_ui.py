from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QButtonGroup
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtWidgets import QFrame
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtWidgets import QListWidget
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QRadioButton
from PyQt6.QtWidgets import QSpinBox
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.qt.widgets.clickablelabel import ClickableLabel
from src.replays.replaydetails.rangeslider import RangeSlider


class HostGameDialogUi:
    def setupUi(self, widget: QWidget) -> None:
        main_layout = QVBoxLayout(widget)
        main_layout.setSpacing(12)

        top_section = QFrame()
        top_layout = QVBoxLayout(top_section)
        top_layout.setContentsMargins(15, 15, 15, 15)

        game_name_label = QLabel("Game Title")
        game_name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

        self.titleEdit = QLineEdit()
        self.titleEdit.setFont(QFont("Segoe UI", 11))
        self.titleEdit.setMaxLength(25)
        self.titleEdit.setPlaceholderText("[REQUIRED] Enter game name...")

        options_layout = QHBoxLayout()

        self.radioPublic = QRadioButton("Public")
        self.radioPublic.setChecked(True)
        self.radioFriends = QRadioButton("Friends only")

        self.visibility_group = QButtonGroup()
        self.visibility_group.addButton(self.radioPublic)
        self.visibility_group.addButton(self.radioFriends)

        self.passCheck = QCheckBox("Password")
        self.passEdit = QLineEdit()
        self.passEdit.setMaxLength(25)
        self.passEdit.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.passEdit.setEnabled(False)
        self.passEdit.setPlaceholderText("Enter password...")
        self.passEdit.setMaximumWidth(120)

        self.enforceRatingCheck = QCheckBox("Enforce Player Rating")

        self.ratingMinSpinBox = QSpinBox()
        self.ratingMinSpinBox.setMinimum(-9999)
        self.ratingMinSpinBox.setMaximum(9999)
        self.ratingMinSpinBox.setValue(800)
        self.ratingMinSpinBox.setEnabled(False)

        self.ratingMaxSpinBox = QSpinBox()
        self.ratingMaxSpinBox.setMinimum(-9999)
        self.ratingMaxSpinBox.setMaximum(9999)
        self.ratingMaxSpinBox.setValue(1500)
        self.ratingMaxSpinBox.setEnabled(False)

        options_layout.addWidget(self.radioPublic)
        options_layout.addWidget(self.radioFriends)
        options_layout.addStretch()
        options_layout.addWidget(self.passCheck)
        options_layout.addWidget(self.passEdit)
        options_layout.addWidget(self.enforceRatingCheck)
        options_layout.addWidget(self.ratingMinSpinBox)
        options_layout.addWidget(self.ratingMaxSpinBox)

        top_layout.addWidget(game_name_label)
        top_layout.addWidget(self.titleEdit)
        top_layout.addLayout(options_layout)

        middle_section = QHBoxLayout()
        middle_section.setSpacing(6)

        self.mapsGroup = QGroupBox("Maps")
        self.mapsGroup.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        maps_layout = QVBoxLayout(self.mapsGroup)
        maps_layout.setContentsMargins(10, 15, 10, 10)

        self.mapFiltersButton = QPushButton("Filters")
        maps_layout.addWidget(self.mapFiltersButton)

        self.mapFiltersWidget = QWidget()
        map_filters_layout = QGridLayout(self.mapFiltersWidget)
        map_filters_layout.setSpacing(8)

        map_filters_layout.addWidget(QLabel("Width:"), 0, 0)
        map_width_layout = QHBoxLayout()
        self.mapWidthSlider = RangeSlider(Qt.Orientation.Horizontal)
        self.mapWidthSlider.setMinimum(0)
        self.mapWidthSlider.setMaximum(100)
        self.mapWidthMinimum = QSpinBox()
        self.mapWidthMinimum.setMinimum(0)
        self.mapWidthMaximum = QSpinBox()
        self.mapWidthMaximum.setMaximum(100)
        self.mapWidthMaximum.setValue(100)
        map_width_layout.addWidget(self.mapWidthMinimum)
        map_width_layout.addWidget(self.mapWidthMaximum)
        map_filters_layout.addLayout(map_width_layout, 0, 1)
        map_filters_layout.addWidget(self.mapWidthSlider, 1, 0, 1, 2)
        map_filters_layout.addWidget(QLabel("Height:"), 2, 0)
        map_height_layout = QHBoxLayout()
        self.mapHeightSlider = RangeSlider(Qt.Orientation.Horizontal)
        self.mapHeightMinimum = QSpinBox()
        self.mapHeightMinimum.setMinimum(0)
        self.mapHeightMaximum = QSpinBox()
        self.mapHeightMaximum.setMaximum(100)
        self.mapHeightMaximum.setValue(100)
        map_height_layout.addWidget(self.mapHeightMinimum)
        map_height_layout.addWidget(self.mapHeightMaximum)
        map_filters_layout.addLayout(map_height_layout, 2, 1)
        map_filters_layout.addWidget(self.mapHeightSlider, 3, 0, 1, 2)

        map_filters_layout.addWidget(QLabel("Players:"), 4, 0)
        map_players_layout = QHBoxLayout()
        self.mapPlayersMinimum = QSpinBox()
        self.mapPlayersMinimum.setMinimum(0)
        self.mapPlayersMaximum = QSpinBox()
        self.mapPlayersMaximum.setMaximum(16)
        self.mapPlayersMaximum.setValue(16)
        self.mapPlayersSlider = RangeSlider(Qt.Orientation.Horizontal)
        self.mapPlayersSlider.setMaximum(16)
        map_players_layout.addWidget(self.mapPlayersMinimum)
        map_players_layout.addWidget(self.mapPlayersMaximum)
        map_filters_layout.addLayout(map_players_layout, 4, 1)
        map_filters_layout.addWidget(self.mapPlayersSlider, 5, 0, 1, 2)
        self.resetMapFiltersButton = QPushButton("Reset Filters")
        map_filters_layout.addWidget(self.resetMapFiltersButton, 6, 1, 1, 1)
        maps_layout.addWidget(self.mapFiltersWidget)

        self.mapNameFilter = QLineEdit()
        self.mapNameFilter.setPlaceholderText("Search maps...")
        maps_layout.addWidget(self.mapNameFilter)

        self.mapList = QListWidget()
        self.mapList.setMinimumWidth(256)
        self.mapList.setAlternatingRowColors(True)
        maps_layout.addWidget(self.mapList)

        maps_bottom_layout = QHBoxLayout()
        self.generateButton = QPushButton("Map Generator")
        self.generateButton.setMaximumWidth(120)
        self.generateButton.setMinimumWidth(100)
        self.mapsLoadingLabel = QLabel("Loading maps...")
        self.mapsLoadingLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mapsLoadingLabel.setObjectName("labelLoading")
        self.selectRandomMapButton = QPushButton("Select Random Map")
        maps_bottom_layout.addWidget(self.generateButton)
        maps_bottom_layout.addStretch()
        maps_bottom_layout.addWidget(self.mapsLoadingLabel)
        maps_bottom_layout.addWidget(self.selectRandomMapButton)
        maps_layout.addLayout(maps_bottom_layout)

        self.previewGroup = QGroupBox("Map Preview")
        self.previewGroup.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        preview_layout = QVBoxLayout(self.previewGroup)
        preview_layout.setContentsMargins(10, 15, 10, 10)

        self.mapPreviewLabel = ClickableLabel()
        self.mapPreviewLabel.setFixedSize(256, 256)
        self.mapPreviewLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mapPreviewLabel.setProperty("bordered", "true")
        self.mapPreviewLabel.setText("Select a map to preview")

        map_info_layout = QHBoxLayout()
        map_info_layout.addStretch()
        self.mapSizeLabel = QLabel("-")
        map_info_layout.addWidget(self.mapSizeLabel)

        self.mapPlayersLabel = QLabel("-")
        map_info_layout.addWidget(self.mapPlayersLabel)

        self.mapVersionLabel = QLabel("-")
        map_info_layout.addWidget(self.mapVersionLabel)
        map_info_layout.addStretch()

        self.mapNameLabel = QLabel("No map selected")
        self.mapNameLabel.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.mapNameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.mapDescription = QTextEdit("No description available")
        self.mapDescription.setReadOnly(True)
        self.mapDescription.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.mapDescription.setMinimumHeight(120)
        self.mapDescription.setFixedWidth(390)

        preview_layout.addWidget(self.mapPreviewLabel, alignment=Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.mapNameLabel)
        preview_layout.addLayout(map_info_layout)
        preview_layout.addWidget(self.mapDescription)

        mods_group = QGroupBox("Mods")
        mods_group.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        mods_layout = QVBoxLayout(mods_group)
        mods_layout.setContentsMargins(10, 15, 10, 10)

        mod_filters_layout = QGridLayout()
        mod_filters_layout.setSpacing(8)

        mod_filters_layout.addWidget(QLabel("Type:"), 0, 0)

        mod_type_layout = QHBoxLayout()
        self.modAllRadio = QRadioButton("All")
        self.modAllRadio.setChecked(True)
        self.modUiRadio = QRadioButton("UI")
        self.modSimRadio = QRadioButton("SIM")

        self.modTypeRadioGroup = QButtonGroup()
        self.modTypeRadioGroup.addButton(self.modAllRadio)
        self.modTypeRadioGroup.addButton(self.modUiRadio)
        self.modTypeRadioGroup.addButton(self.modSimRadio)

        mod_type_layout.addStretch()
        mod_type_layout.addWidget(self.modAllRadio)
        mod_type_layout.addWidget(self.modUiRadio)
        mod_type_layout.addWidget(self.modSimRadio)

        mod_filters_layout.addLayout(mod_type_layout, 0, 1, 1, 2)

        self.modNameFilter = QLineEdit()
        self.modNameFilter.setPlaceholderText("Search mods...")
        mod_filters_layout.addWidget(self.modNameFilter, 1, 0, 1, 3)

        mods_layout.addLayout(mod_filters_layout)

        self.modList = QListWidget()
        self.modList.setMinimumWidth(256)
        self.modList.setMinimumHeight(350)
        self.modList.setAlternatingRowColors(True)
        self.modList.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        mods_controls = QHBoxLayout()
        self.deselectUiMods = QPushButton("Deselect all UI mods")
        self.deselectSimMods = QPushButton("Deselect all SIM mods")
        mods_controls.addWidget(self.deselectUiMods)
        mods_controls.addWidget(self.deselectSimMods)

        mods_layout.addWidget(self.modList)
        mods_layout.addLayout(mods_controls)

        middle_section.addWidget(self.mapsGroup, 1)
        middle_section.addWidget(self.previewGroup, 0)
        middle_section.addWidget(mods_group, 1)

        bottom_layout = QHBoxLayout()

        self.saveAndCloseButton = QPushButton("Save settings and Close")
        self.saveAndCloseButton.setObjectName("saveHostGameSettingsButton")
        self.saveAndCloseButton.setMinimumHeight(30)

        self.hostButton = QPushButton("Host Game")
        self.hostButton.setObjectName("hostGameButton")
        self.hostButton.setMinimumSize(120, 35)

        bottom_layout.addStretch()
        bottom_layout.addWidget(self.saveAndCloseButton)
        bottom_layout.addWidget(self.hostButton)

        main_layout.addWidget(top_section)
        main_layout.addLayout(middle_section)
        main_layout.addLayout(bottom_layout)
