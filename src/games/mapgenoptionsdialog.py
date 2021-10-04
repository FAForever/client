from enum import Enum

from PyQt5 import QtCore, QtWidgets

import config
import util

FormClass, BaseClass = util.THEME.loadUiType("games/mapgen.ui")


class MapStyle(Enum):
    RANDOM = "RANDOM"
    DEFAULT = "DEFAULT"
    ONE_ISLAND = "ONE_ISLAND"
    BIG_ISLANDS = "BIG_ISLANDS"
    SMALL_ISLANDS = "SMALL_ISLANDS"
    CENTER_LAKE = "CENTER_LAKE"
    VALLEY = "VALLEY"
    DROP_PLATEAU = "DROP_PLATEAU"
    LITTLE_MOUNTAIN = "LITTLE_MOUNTAIN"
    MOUNTAIN_RANGE = "MOUNTAIN_RANGE"
    LAND_BRIDGE = "LAND_BRIDGE"
    LOW_MEX = "LOW_MEX"
    FLOODED = "FLOODED"

    def getMapStyle(index):
        return list(MapStyle)[index]


class MapGenDialog(FormClass, BaseClass):
    def __init__(self, parent, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)

        util.THEME.stylesheets_reloaded.connect(self.load_stylesheet)
        self.load_stylesheet()

        self.parent = parent

        self.generationType.currentIndexChanged.connect(
            self.generationTypeChanged,
        )
        self.numberOfSpawns.currentIndexChanged.connect(
            self.numberOfSpawnsChanged,
        )
        self.mapSize.valueChanged.connect(self.mapSizeChanged)
        self.mapStyle.currentIndexChanged.connect(self.mapStyleChanged)
        self.generateMapButton.clicked.connect(self.generateMap)
        self.saveMapGenSettingsButton.clicked.connect(self.saveMapGenPrefs)
        self.resetMapGenSettingsButton.clicked.connect(self.resetMapGenPrefs)

        self.random_buttons = [
            self.landRandomDensity,
            self.plateausRandomDensity,
            self.mountainsRandomDensity,
            self.rampsRandomDensity,
            self.mexRandomDensity,
            self.reclaimRandomDensity,
        ]
        self.sliders = [
            self.landDensity,
            self.plateausDensity,
            self.mountainsDensity,
            self.rampsDensity,
            self.mexDensity,
            self.reclaimDensity,
        ]

        self.option_frames = [
            self.landOptions,
            self.plateausOptions,
            self.mountainsOptions,
            self.rampsOptions,
            self.mexOptions,
            self.reclaimOptions,
        ]

        for random_button in self.random_buttons:
            random_button.setChecked(
                config.Settings.get(
                    "mapGenerator/{}".format(random_button.objectName()),
                    type=bool,
                    default=True,
                ),
            )
            random_button.toggled.connect(self.configOptionFrames)

        for slider in self.sliders:
            slider.setValue(
                config.Settings.get(
                    "mapGenerator/{}".format(slider.objectName()),
                    type=int,
                    default=0,
                ),
            )

        self.generation_type = "casual"
        self.number_of_spawns = 2
        self.map_size = 256
        self.map_style = MapStyle.RANDOM
        self.generationType.setCurrentIndex(
            config.Settings.get(
                "mapGenerator/generationTypeIndex", type=int, default=0,
            ),
        )
        self.numberOfSpawns.setCurrentIndex(
            config.Settings.get(
                "mapGenerator/numberOfSpawnsIndex", type=int, default=0,
            ),
        )
        self.mapSize.setValue(
            config.Settings.get(
                "mapGenerator/mapSize", type=float, default=5.0,
            ),
        )
        self.mapStyle.setCurrentIndex(
            config.Settings.get(
                "mapGenerator/mapStyleIndex", type=int, default=0,
            ),
        )

        self.configOptionFrames()

    def load_stylesheet(self):
        self.setStyleSheet(util.THEME.readstylesheet("client/client.css"))

    def keyPressEvent(self, event):
        if (
            event.key() == QtCore.Qt.Key_Enter
            or event.key() == QtCore.Qt.Key_Return
        ):
            return
        QtWidgets.QDialog.keyPressEvent(self, event)

    @QtCore.pyqtSlot(int)
    def numberOfSpawnsChanged(self, index):
        self.number_of_spawns = 2 * (index + 1)

    @QtCore.pyqtSlot(float)
    def mapSizeChanged(self, value):
        if (value % 1.25):
            # nearest to multiple of 1.25
            value = ((value + 0.625) // 1.25) * 1.25
            self.mapSize.blockSignals(True)
            self.mapSize.setValue(value)
            self.mapSize.blockSignals(False)
        self.map_size = int(value * 51.2)

    @QtCore.pyqtSlot(int)
    def generationTypeChanged(self, index):
        if index == -1 or index == 0:
            self.generation_type = "casual"
        elif index == 1:
            self.generation_type = "tournament"
        elif index == 2:
            self.generation_type = "blind"
        elif index == 3:
            self.generation_type = "unexplored"

        if index == -1 or index == 0:
            self.mapStyle.setEnabled(True)
            self.mapStyle.setCurrentIndex(
                config.Settings.get(
                    "mapGenerator/mapStyleIndex", type=int, default=0,
                ),
            )
        else:
            self.mapStyle.setEnabled(False)
            self.mapStyle.setCurrentIndex(0)

        self.checkRandomButtons()

    @QtCore.pyqtSlot(int)
    def mapStyleChanged(self, index):
        if index == -1 or index == 0:
            self.map_style = MapStyle.RANDOM
        else:
            self.map_style = MapStyle.getMapStyle(index)

        self.checkRandomButtons()

    @QtCore.pyqtSlot()
    def checkRandomButtons(self):
        for random_button in self.random_buttons:
            if (
                self.generation_type != "casual"
                or self.map_style != MapStyle.RANDOM
            ):
                random_button.setEnabled(False)
                random_button.setChecked(True)
            else:
                random_button.setEnabled(True)
                random_button.setChecked(
                    config.Settings.get(
                        "mapGenerator/{}".format(random_button.objectName()),
                        type=bool,
                        default=True,
                    ),
                )

    @QtCore.pyqtSlot()
    def configOptionFrames(self):
        for random_button in self.random_buttons:
            option_frame = self.option_frames[
                self.random_buttons.index(random_button)
            ]
            if random_button.isChecked():
                option_frame.setEnabled(False)
            else:
                option_frame.setEnabled(True)

    @QtCore.pyqtSlot()
    def saveMapGenPrefs(self):
        config.Settings.set(
            "mapGenerator/generationTypeIndex",
            self.generationType.currentIndex(),
        )
        config.Settings.set(
            "mapGenerator/mapSize",
            self.mapSize.value(),
        )
        config.Settings.set(
            "mapGenerator/numberOfSpawnsIndex",
            self.numberOfSpawns.currentIndex(),
        )
        config.Settings.set(
            "mapGenerator/mapStyleIndex",
            self.mapStyle.currentIndex(),
        )
        for random_button in self.random_buttons:
            config.Settings.set(
                "mapGenerator/{}".format(random_button.objectName()),
                random_button.isChecked(),
            )
        for slider in self.sliders:
            config.Settings.set(
                "mapGenerator/{}".format(slider.objectName()), slider.value(),
            )
        self.done(1)

    @QtCore.pyqtSlot()
    def resetMapGenPrefs(self):
        self.generationType.setCurrentIndex(0)
        self.mapSize.setValue(5.0)
        self.numberOfSpawns.setCurrentIndex(0)
        self.mapStyle.setCurrentIndex(0)

        for random_button in self.random_buttons:
            random_button.setChecked(True)
        for slider in self.sliders:
            slider.setValue(0)

    @QtCore.pyqtSlot()
    def generateMap(self):
        map_ = self.parent.client.map_generator.generateMap(
            args=self.setArguments(),
        )
        if map_:
            self.parent.setupMapList()
            self.parent.set_map(map_)
            self.saveMapGenPrefs()

    def setArguments(self):
        args = []
        args.append("--map-size")
        args.append(str(self.map_size))
        args.append("--spawn-count")
        args.append(str(self.number_of_spawns))

        if self.map_style != MapStyle.RANDOM:
            args.append("--style")
            args.append(self.map_style.value)
        else:
            if self.generation_type == "tournament":
                args.append("--tournament-style")
            elif self.generation_type == "blind":
                args.append("--blind")
            elif self.generation_type == "unexplored":
                args.append("--unexplored")

            slider_args = [
                ["--land-density", None],
                ["--plateau-density", None],
                ["--mountain-density", None],
                ["--ramp-density", None],
                ["--mex-density", None],
                ["--reclaim-density", None],
            ]
            for index, slider in enumerate(self.sliders):
                if slider.isEnabled():
                    if slider == self.landDensity:
                        value = float(1 - (slider.value() / 127))
                    else:
                        value = float(slider.value() / 127)
                    slider_args[index][1] = value

            for arg_key, arg_value in slider_args:
                if arg_value is not None:
                    args.append(arg_key)
                    args.append(str(arg_value))

        return args
