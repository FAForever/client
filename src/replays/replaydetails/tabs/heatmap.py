import os
from collections import Counter
from functools import partial
from typing import NamedTuple

import pyqtgraph as pg
from PyQt6.QtCore import QSize
from PyQt6.QtCore import Qt
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtGui import QTransform
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtWidgets import QDoubleSpinBox
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtWidgets import QSlider
from PyQt6.QtWidgets import QSpinBox
from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.config import Settings
from src.fa.maps import folderForMap
from src.fa.maps_.preview import create_large_preview
from src.qt.utils import block_signals
from src.replays.replaydetails.helpers import seconds_to_human
from src.replays.replaydetails.rangeslider import RangeSlider
from src.replays.replaydetails.replayformat import cmdTypeToString
from src.replays.replaydetails.replayreader import ReplayParser

try:
    from scipy_ndimage.ndimage._filters import gaussian_filter
except ImportError:
    from scipy.ndimage import gaussian_filter


def create_colorbar_hist() -> pg.HistogramLUTWidget:
    hist = pg.HistogramLUTWidget()
    cmap_name = Settings.get("replaycard.heatmap/colormap", "preset-gradient:flame")
    if cmap_name.startswith("preset-gradient"):
        hist.item.gradient.loadPreset(cmap_name.split(":")[1])
    elif cmap_name:
        cmap = pg.colormap.get(cmap_name)
        hist.item.gradient.setColorMap(cmap)
        hist.item.gradient.showTicks(False)
    hist.item.gradient.menu.sigColorMapTriggered.connect(
        lambda colormap: Settings.set("replaycard.heatmap/colormap", colormap.name),
    )
    return hist


class HeatmapProperties(NamedTuple):
    width: int = 1024
    height: int = 1024

    def size(self) -> QSize:
        return QSize(self.width, self.height)

    def get_scale(self) -> int:
        """Relative size to the standard 256x256 dds pixmap"""
        return (self.height) // 256


class Heatmap(QWidget):
    def __init__(self) -> None:
        QWidget.__init__(self)
        self.viewbox = pg.ViewBox()
        self.heatmap = pg.ImageItem()
        self.viewbox.addItem(self.heatmap)

        _graphics_layout = QGridLayout()
        _graphics_layout.setSpacing(6)
        _graphics_view = pg.GraphicsView()
        _graphics_view.setCentralItem(self.viewbox)

        _graphics_layout.addWidget(_graphics_view, 0, 0, 7, 1)

        self.hist = create_colorbar_hist()
        self.hist.setImageItem(self.heatmap)
        _graphics_layout.addWidget(self.hist, 0, 1)

        self.filter_tab_widget = QTabWidget()
        self.filter_tab_widget.setMaximumWidth(270)

        self.commands_scroll_area = QScrollArea()
        self.commands_scroll_area.setWidgetResizable(True)
        self.commands_scroll_area.setContentsMargins(0, 0, 0, 0)

        self.commands_tab = QWidget()
        self.commands_tab.setObjectName("overview_widget")
        commands_layout = QVBoxLayout(self.commands_tab)

        self.commands_scroll_area.setWidget(self.commands_tab)

        self.visible_commands = Settings.get(
            "replaycard.heatmap/visible_commands",
            default=[1] * len(cmdTypeToString),
            type=list,
        )

        self.all_cmds_checkbox = QCheckBox("Select All")
        self.all_cmds_checkbox.setChecked(all(self.visible_commands))
        self.all_cmds_checkbox.checkStateChanged.connect(self.on_select_all_cmds)

        commands_layout.addWidget(self.all_cmds_checkbox)
        commands_layout.addSpacing(6)

        self.cmds_checkboxes: dict[str, QCheckBox] = {}
        for index, cmd_type in enumerate(cmdTypeToString):
            if index == 0:
                continue
            checkbox = QCheckBox(cmd_type)
            checkbox.setObjectName(str(index))
            checkbox.setChecked(bool(self.visible_commands[index]))
            self.cmds_checkboxes[cmd_type] = checkbox
            checkbox.checkStateChanged.connect(partial(self.on_cmd_type_changed, box=checkbox))
        for _, box in sorted(self.cmds_checkboxes.items()):
            commands_layout.addWidget(box)

        self.players_scroll_area = QScrollArea()
        self.players_scroll_area.setWidgetResizable(True)
        self.players_scroll_area.setContentsMargins(0, 0, 0, 0)

        self.players_tab = QWidget()
        self.players_tab.setObjectName("overview_widget")
        players_layout = QVBoxLayout(self.players_tab)

        self.players_scroll_area.setWidget(self.players_tab)

        self.visible_players = [1] * 16

        self.all_players_checkbox = QCheckBox("Select All")
        self.all_players_checkbox.checkStateChanged.connect(self.on_select_all_players)

        players_layout.addWidget(self.all_players_checkbox)
        players_layout.addSpacing(6)

        self.players_checkboxes: dict[int, QCheckBox] = {}
        for i in range(16):
            checkbox = QCheckBox(str(i))
            checkbox.setObjectName(str(i))
            checkbox.setChecked(True)
            self.players_checkboxes[i] = checkbox
            checkbox.checkStateChanged.connect(partial(self.on_player_changed, box=checkbox))
            players_layout.addWidget(checkbox)
        players_layout.addStretch()

        self.filter_tab_widget.addTab(self.players_scroll_area, "Players")
        self.filter_tab_widget.addTab(self.commands_scroll_area, "Commands")

        _graphics_layout.addWidget(self.filter_tab_widget, 0, 2)

        self.foreground_control = QCheckBox("Foreground (map layer)")
        show_foreground = Settings.get("replaycard.heatmap/foreground", True, type=bool)
        self.foreground_control.setChecked(show_foreground)
        self.foreground_control.checkStateChanged.connect(self.on_foreground_checked)
        _graphics_layout.addWidget(self.foreground_control, 1, 2)

        _graphics_layout.addWidget(QLabel("Foreground opacity: "), 2, 2)

        foreground_opacity_layout = QHBoxLayout()

        self.opacity_spin_box = QDoubleSpinBox()
        self.opacity_spin_box.setMinimum(0)
        self.opacity_spin_box.setMaximum(1)
        self.opacity_spin_box.setSingleStep(0.01)
        self.opacity_spin_box.setMaximumWidth(50)
        opacity = Settings.get("replaycard.heatmap/foreground_opacity", 20, type=int)
        self.opacity_spin_box.setValue(opacity / 100)
        self.opacity_spin_box.valueChanged.connect(self.on_spinbox_opacity_changed)
        self.opacity_spin_box.setEnabled(show_foreground)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(opacity)
        self.opacity_slider.setMaximumWidth(194)
        self.opacity_slider.valueChanged.connect(self.on_opacity_slider_changed)
        self.opacity_slider.setEnabled(show_foreground)
        foreground_opacity_layout.addWidget(self.opacity_slider, 3)
        foreground_opacity_layout.addWidget(self.opacity_spin_box)
        foreground_opacity_layout.setContentsMargins(0, 0, 0, 0)
        _graphics_layout.addLayout(foreground_opacity_layout, 3, 2)

        self.foreground_image = pg.QtWidgets.QGraphicsPixmapItem()
        self.foreground_image.setZValue(1)
        self.foreground_image.setOpacity(self.opacity_spin_box.value())
        visible = Settings.get("replaycard.heatmap/foreground", default=True, type=bool)
        self.foreground_image.setVisible(visible)
        self.rotate_transform = QTransform().scale(1, -1)
        self.viewbox.addItem(self.foreground_image)

        self.smooth_check_box = QCheckBox("Smoothing")
        smoothing = Settings.get("replaycard.heatmap/smoothing", True, type=bool)
        self.smooth_check_box.setChecked(smoothing)
        self.smooth_check_box.checkStateChanged.connect(self.generate_new_heatmap)
        self.smooth_check_box.checkStateChanged.connect(
            lambda state: Settings.set(
                "replaycard.heatmap/smoothing",
                state == Qt.CheckState.Checked,
            ),
        )
        _graphics_layout.addWidget(self.smooth_check_box, 1, 1)

        debounce_layout = QHBoxLayout()

        self.debounce_check_box = QCheckBox("Debounce:")
        debounce_tooltip = "Delay between selecting time range and applying smoothing"
        self.debounce_check_box.setToolTip(debounce_tooltip)
        debounce = Settings.get("replaycard.heatmap/debounce", True, type=bool)
        self.debounce_check_box.setChecked(debounce)
        self.debounce_check_box.checkStateChanged.connect(
            lambda state: Settings.set(
                "replaycard.heatmap/debounce",
                state == Qt.CheckState.Checked,
            ),
        )

        self.debounce_spin_box = QSpinBox()
        self.debounce_spin_box.setMinimum(0)
        self.debounce_spin_box.setMaximum(1000)
        debounce_time_ms = Settings.get("replaycard.heatmap/debounce_time_ms", 100, type=int)
        self.debounce_spin_box.setValue(debounce_time_ms)
        self.debounce_spin_box.setSuffix(" ms")
        self.debounce_spin_box.valueChanged.connect(
            lambda value: Settings.set("replaycard.heatmap/debounce_time_ms", value),
        )

        debounce_layout.addWidget(self.debounce_check_box)
        debounce_layout.addWidget(self.debounce_spin_box)
        _graphics_layout.addItem(debounce_layout, 2, 1)

        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.generate_new_heatmap)

        sigma_layout = QHBoxLayout()
        self.x_sigma = QSpinBox()
        self.x_sigma.setObjectName("x_sigma")
        self.y_sigma = QSpinBox()
        self.y_sigma.setObjectName("y_sigma")

        kernel_settings = (self.x_sigma, self.y_sigma)
        for setting in kernel_settings:
            name = setting.objectName()
            setting.setMinimum(0)
            setting.setMaximum(100)
            setting.setPrefix(f"{name.split('_')[0]}: ")
            setting.setValue(Settings.get(f"replaycard.heatmap/{name}", 2, type=int))
            sigma_layout.addWidget(setting)
        self.x_sigma.valueChanged.connect(
            lambda value: Settings.set("replaycard.heatmap/x_sigma", value),
        )
        self.y_sigma.valueChanged.connect(
            lambda value: Settings.set("replaycard.heatmap/y_sigma", value),
        )

        self.regen_button = QPushButton("Regenerate heatmap")
        self.regen_button.clicked.connect(self.generate_new_heatmap)

        _graphics_layout.addWidget(QLabel("Standard deviation for Gaussian kernel:"), 4, 1)
        _graphics_layout.addItem(sigma_layout, 5, 1)
        _graphics_layout.addWidget(self.regen_button, 6, 1)

        self.heatmapRangeSlider = RangeSlider()
        self.heatmapRangeSlider.set_page_step(1000)
        self.heatmapRangeSlider.setOrientation(Qt.Orientation.Horizontal)
        self.heatmapRangeSlider.sliderMoved.connect(self.debounce)
        self.heatmapSliderText = QLabel()
        self.heatmapSliderText.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.heatmapSliderText.setMaximumHeight(12)

        heatmapTabLayout = QVBoxLayout()

        heatmapTabLayout.addItem(_graphics_layout)
        heatmapTabLayout.addWidget(self.heatmapRangeSlider)
        heatmapTabLayout.addWidget(self.heatmapSliderText)

        self.setLayout(heatmapTabLayout)
        self.heatmap_properties = HeatmapProperties()

        self.pts_norm = []

    def initialize(self, replay: ReplayParser) -> None:
        self.set_pts(replay)
        self.setup_players_filter(replay)
        self.create_heatmap(replay.ticks)
        self.set_map_foreground(replay)

    def setup_players_filter(self, replay: ReplayParser) -> None:
        self.all_players_checkbox.setChecked(True)
        for index, checkbox in self.players_checkboxes.items():
            try:
                checkbox.setText(replay.players[index])
                checkbox.show()
            except KeyError:
                checkbox.hide()

    def on_cmd_type_changed(self, state: Qt.CheckState, box: QCheckBox) -> None:
        show = state == Qt.CheckState.Checked
        self.visible_commands[int(box.objectName())] = show
        if not show:
            with block_signals(self.all_cmds_checkbox) as b:
                b.setChecked(False)
        self.generate_new_heatmap()

    def on_select_all_cmds(self, state: Qt.CheckState) -> None:
        show = state == Qt.CheckState.Checked
        for box in self.cmds_checkboxes.values():
            with block_signals(box) as b:
                b.setChecked(show)
                self.visible_commands[int(b.objectName())] = show
        self.generate_new_heatmap()

    def on_player_changed(self, state: Qt.CheckState, box: QCheckBox) -> None:
        show = state == Qt.CheckState.Checked
        self.visible_players[int(box.objectName())] = show
        if not show:
            with block_signals(self.all_players_checkbox) as b:
                b.setChecked(False)
        self.generate_new_heatmap()

    def on_select_all_players(self, state: Qt.CheckState) -> None:
        show = state == Qt.CheckState.Checked
        for box in self.players_checkboxes.values():
            with block_signals(box) as b:
                b.setChecked(show)
                self.visible_players[int(b.objectName())] = show
        self.generate_new_heatmap()

    def save_settings(self) -> None:
        with Settings.group("replaycard.heatmap") as group:
            group.setValue("foreground", self.foreground_control.isChecked())
            group.setValue("foreground_opacity", self.opacity_slider.value())
            group.setValue("visible_commands", self.visible_commands)

    def on_foreground_checked(self, state: Qt.CheckState) -> None:
        show = state == Qt.CheckState.Checked
        self.foreground_image.setVisible(show)
        self.opacity_spin_box.setEnabled(show)
        self.opacity_slider.setEnabled(show)

    def on_spinbox_opacity_changed(self, value: float) -> None:
        self.foreground_image.setOpacity(value)
        with block_signals(self.opacity_slider) as slider:
            slider.setValue(int(value * 100))

    def on_opacity_slider_changed(self, value: int) -> None:
        self.foreground_image.setOpacity(value / 100)
        with block_signals(self.opacity_spin_box) as box:
            box.setValue(value / 100)

    def generate_new_heatmap(self) -> None:
        if len(self.pts_norm) == 0:
            return

        lowtick = self.heatmapRangeSlider.low()
        hightick = self.heatmapRangeSlider.high()
        filtered_pts = self.filter_points(lowtick, hightick)
        img = self.make_image_data(filtered_pts)

        if self.smooth_check_box.isChecked() and not self.debounce_timer.isActive():
            img = gaussian_filter(img, (self.x_sigma.value(), self.y_sigma.value()))
            self.heatmap.setImage(img)
        else:
            mx = max(filtered_pts.values() or [255])
            self.heatmap.setImage(img, levels=[0, mx])

        self.heatmapSliderText.setText(
            f"{seconds_to_human(lowtick // 10)}"
            f"({lowtick})"
            f"{seconds_to_human(hightick // 10)}"
            f"({hightick})",
        )

    def debounce(self) -> None:
        self.generate_new_heatmap()
        if self.debounce_check_box.isChecked():
            self.debounce_timer.start(self.debounce_spin_box.value())

    def set_pts(self, replay: ReplayParser) -> None:
        map_size = replay.map_pixel_size()
        self.pts_norm = self.points_normalized(replay.pts, map_size.width(), map_size.height())
        max_sigma = (len(replay.pts) + 1) // 6
        with block_signals(self.x_sigma) as x, block_signals(self.y_sigma) as y:
            x.setMaximum(max_sigma)
            y.setMaximum(max_sigma)

    def points_normalized(
            self,
            pts: list[tuple[int, float, float, int, int]],
            max_x: float,
            max_y: float,
    ) -> list[tuple[int, int, int, int, int]]:
        pts.sort(key=lambda elem: elem[0])

        w = self.heatmap_properties.width - 1
        h = self.heatmap_properties.height - 1

        return [
            (
                tick,
                # minmaxing, because negative values were spotted (maybe offmapping)
                # example replay: 25037207
                min(max(0, round((x / max_x) * w)), w),
                min(max(0, round((1 - (y / max_y)) * h)), h),
                cmd_type,
                source,
            )
            for tick, x, y, cmd_type, source in pts
        ]

    def create_heatmap(self, ticks: int) -> None:
        self.heatmapRangeSlider.setMinimum(0)
        self.heatmapRangeSlider.setMaximum(ticks)
        self.heatmapRangeSlider.setLow(0)
        self.heatmapRangeSlider.setHigh(ticks)
        self.generate_new_heatmap()

    def set_map_foreground(self, replay: ReplayParser) -> None:
        folder = folderForMap(replay.map_folder_name())
        if folder is None or not os.path.exists(folder):
            self.foreground_image.setPixmap(QPixmap())
            return
        scale = self.heatmap_properties.get_scale()
        pixmap = create_large_preview(folder, scale=scale).scaled(
            self.heatmap_properties.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.foreground_image.setPixmap(pixmap.transformed(self.rotate_transform))

    def make_image_data(self, pts: Counter[tuple[int, int]]) -> pg.numpy.ndarray:
        pixels = pg.numpy.zeros((self.heatmap_properties.width, self.heatmap_properties.height))
        for (x, y), count in pts.items():
            pixels[x][y] += count
        return pixels

    def filter_points(self, fromTick: int, toTick: int) -> Counter[tuple[int, int]]:
        return Counter(
            (x, y)
            for (tick, x, y, cmd_type, source) in self.pts_norm
            if (
                self.visible_commands[cmd_type]
                and self.visible_players[source]
                and fromTick < tick < toTick
            )
        )
