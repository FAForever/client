from itertools import product

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtWidgets import QStackedWidget
from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.qt.graphics.labeledbargraphitem import LabeledBarGraphItem
from src.replays.replaydetails.replayreader import ReplayParser
from src.replays.replaydetails.tabs.gamestats_types import GameStats

UNIT_TYPES = {
    "land": "Land",
    "air": "Air",
    "naval": "Naval",
    "tech1": "Tech 1",
    "tech2": "Tech 2",
    "tech3": "Tech 3",
    "experimental": "Experimental",
    "transportation": "Transportation",
    "engineer": "Engineer",
    "structures": "Structures",
    "cdr": "ACUs",
    "sacu": "SACUs",
}

BAR_GROUP_WIDTH = 0.8


class PlotsUI:
    def setupUi(self, widget: QWidget) -> None:
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()

        score_tab = QWidget()
        self.scoreLayout = QVBoxLayout(score_tab)
        self.scoreLayout.setContentsMargins(0, 0, 0, 0)
        self.tabs.addTab(score_tab, "Scores")

        resource_tab = QWidget()
        self.resourceLayout = QGridLayout(resource_tab)
        self.resourceLayout.setContentsMargins(0, 0, 0, 0)
        self.tabs.addTab(resource_tab, "Resources")

        self.unitsTab = QTabWidget()

        general_units_tab = QWidget()
        self.unitsLayout = QGridLayout(general_units_tab)
        self.unitsLayout.setContentsMargins(0, 0, 0, 0)
        self.unitsTab.addTab(general_units_tab, "General")

        units_breakdown_tab = QWidget()
        units_scroll_layout = QVBoxLayout(units_breakdown_tab)
        units_scroll_layout.setContentsMargins(0, 0, 0, 0)

        units_scroll = QScrollArea()
        units_scroll.setContentsMargins(0, 0, 0, 0)
        units_scroll.setWidgetResizable(True)
        units_scroll_layout.addWidget(units_scroll)

        self.unitsBreakdownWidget = QWidget()
        self.unitsBreakdownWidget.setContentsMargins(0, 0, 0, 0)
        self.unitsBreakdownLayout = QGridLayout(self.unitsBreakdownWidget)
        self.unitsBreakdownLayout.setContentsMargins(0, 0, 0, 0)
        self.unitsBreakdownWidget.setObjectName("statisticsChartsScrollArea")
        units_scroll.setWidget(self.unitsBreakdownWidget)
        self.unitsTab.addTab(units_breakdown_tab, "Breakdown")
        self.tabs.addTab(self.unitsTab, "Units")

        balance_tab = QWidget()
        self.balanceLayout = QGridLayout(balance_tab)
        self.balanceLayout.setContentsMargins(0, 0, 0, 0)
        self.tabs.addTab(balance_tab, "Build vs Loss")
        main_layout.addWidget(self.tabs)


def bar_shift(index: int, total_bars: int, bar_width: float) -> float:
    return (index - total_bars / 2 + 0.5) * bar_width


class PlotsWidget(QWidget):
    def __init__(self) -> None:
        QWidget.__init__(self)
        self.ui = PlotsUI()
        self.ui.setupUi(self)
        self.ui.tabs.currentChanged.connect(self.on_main_tab_changed)
        self.ui.unitsTab.currentChanged.connect(self.on_units_tab_changed)

        self.stats: GameStats = []

        self.tab_history = set()
        self.units_tab_history = set()

        self.tab_fillers = (
            self.add_score_plot,
            self.add_resource_plots,
            self.add_unit_plots,
            self.add_balance_plots,
        )
        self.units_tab_fillers = (
            lambda: None,  # placeholder
            self.add_unit_breakdown_plots,
        )

    def initialize(self, data: dict[str, GameStats]) -> None:
        self.stats = data["stats"]
        self.add_score_plot()
        self.tab_history.add(0)

    def on_units_tab_changed(self, index: int) -> None:
        if index in self.units_tab_history:
            return
        self.units_tab_history.add(index)
        self.units_tab_fillers[index]()

    def on_main_tab_changed(self, index: int) -> None:
        if index in self.tab_history:
            return
        self.tab_history.add(index)
        self.tab_fillers[index]()

    def add_unit_breakdown_plots(self) -> None:
        self.ui.unitsBreakdownWidget.hide()
        bar_width = BAR_GROUP_WIDTH / 3
        player_names = [player["name"] for player in self.stats]
        x_pos = np.arange(len(self.stats))

        for index, (unit_type, title) in enumerate(UNIT_TYPES.items()):
            if unit_type not in self.stats[0]["units"]:
                continue

            plot = pg.PlotWidget(title=title)
            plot.setLabel("left", "Count")
            plot.addLegend()
            plot.setMinimumHeight(300)

            for i, (color, stat) in enumerate(zip(("b", "r", "g"), ("built", "lost", "kills"))):
                values = [player["units"][unit_type][stat] for player in self.stats]
                bar = LabeledBarGraphItem(
                    categories=player_names,
                    x=x_pos + bar_shift(i, 3, bar_width),
                    height=values,
                    width=bar_width,
                    brush=color,
                    name=stat.title(),
                )
                plot.addItem(bar)
            plot.getAxis("bottom").setTicks(
                [[(i, name) for i, name in enumerate(player_names)]],
            )
            self.ui.unitsBreakdownLayout.addWidget(plot, index // 2, index % 2)
        self.ui.unitsBreakdownWidget.show()

    def _create_income_plots(self) -> list[pg.PlotWidget]:
        plots = []

        player_names = [player["name"] for player in self.stats]
        x_pos = np.arange(len(player_names))
        bar_width = BAR_GROUP_WIDTH / 3
        colors = {
            "mass": ("b", "r", "g"),
            "energy": ("y", "m", "c"),
        }
        for resource in ("mass", "energy"):
            plot = pg.PlotWidget(title=f"{resource.capitalize()}")
            plot.setLabel("left", resource)
            plot.addLegend()

            metrics = (
                (f"{resource}in", "total", "Collected"),
                (f"{resource}out", "total", "Spent"),
                (f"{resource}out", "excess", "Wasted"),
            )
            for i, (category, metric, name) in enumerate(metrics):
                values = [player["resources"][category][metric] for player in self.stats]
                bar = LabeledBarGraphItem(
                    categories=player_names,
                    x=x_pos + bar_shift(i, len(metrics), bar_width),
                    height=values,
                    width=bar_width,
                    brush=colors[resource][i],
                    name=name,
                )
                plot.addItem(bar)
            plot.getAxis("bottom").setTicks([[(i, name) for i, name in enumerate(player_names)]])
            plots.append(plot)
        return plots

    def _create_income_breakdown_plots(self) -> list[pg.PlotWidget]:
        plots = []

        player_names = [player["name"] for player in self.stats]
        x_pos = np.arange(len(player_names))
        bar_width = BAR_GROUP_WIDTH / 2

        colors = {
            "mass": ("b", "c"),
            "energy": ("y", "m"),
        }
        for resource in ("mass", "energy"):
            plot = pg.PlotWidget(title=f"{resource.title()} Income Breakdown")
            plot.setLabel("left", resource)
            plot.addLegend()

            total = np.array(
                [player["resources"][f"{resource}in"]["total"] for player in self.stats],
            )
            reclaimed = np.array(
                [player["resources"][f"{resource}in"]["reclaimed"] for player in self.stats],
            )
            produced = total - reclaimed
            for i, (name, val) in enumerate(zip(("Produced", "Reclaimed"), (produced, reclaimed))):
                bar = LabeledBarGraphItem(
                    categories=player_names,
                    x=x_pos + bar_shift(i, 2, bar_width),
                    height=val,
                    width=bar_width,
                    brush=colors[resource][i],
                    name=name,
                )
                plot.addItem(bar)
            plot.getAxis("bottom").setTicks(
                [[(i, name) for i, name in enumerate(player_names)]],
            )
            plots.append(plot)
        return plots

    def add_resource_plots(self) -> None:
        income_plots = self._create_income_plots()
        breakdown_plots = self._create_income_breakdown_plots()
        for index, plot in enumerate(income_plots + breakdown_plots):
            self.ui.resourceLayout.addWidget(plot, index // 2, index % 2)

    def add_unit_plots(self) -> None:
        unit_kinds = {
            "category": (
                "land",
                "air",
                "naval",
            ),
            "tech": (
                "tech1",
                "tech2",
                "tech3",
                "experimental",
            ),
        }
        colors = {
            "land": (0, 255, 0),            # Green
            "air": (100, 100, 255),         # Light Blue
            "naval": (0, 0, 255),           # Dark Blue
            "tech1": (255, 255, 0),         # Yellow
            "tech2": (255, 128, 0),         # Orange
            "tech3": (255, 0, 0),           # Red
            "experimental": (255, 0, 255),  # Magenta
        }

        player_names = [player["name"] for player in self.stats]
        plot_types = ["built", "lost", "kills"]
        x_pos = np.arange(len(player_names))

        enumerator = enumerate(product(plot_types, unit_kinds.items()))
        for index, (plot_type, (subtype, unit_cats)) in enumerator:
            bar_width = BAR_GROUP_WIDTH / len(unit_cats)
            plot = pg.PlotWidget(title=f"Units {plot_type.capitalize()} ({subtype})")
            plot.addLegend()
            plot.setLabel("left", "Units")

            for i, unit_cat in enumerate(unit_cats):
                values = [player["units"][unit_cat][plot_type] for player in self.stats]
                bar = LabeledBarGraphItem(
                    categories=player_names,
                    x=x_pos + bar_shift(i, len(unit_cats), bar_width),
                    height=values,
                    width=bar_width,
                    brush=colors[unit_cat],
                    name=unit_cat,
                )
                plot.addItem(bar)
            plot.getAxis("bottom").setTicks([[(i, name) for i, name in enumerate(player_names)]])
            self.ui.unitsLayout.addWidget(plot, index // 2, index % 2)

    def _create_kd_plot(self) -> pg.PlotWidget:
        player_names = [player["name"] for player in self.stats]
        x_pos = np.arange(len(player_names))

        kd_plot = pg.PlotWidget(title="Kill/Death Ratio (Unit Count)")
        kd_plot.addLegend()
        kd_plot.setLabel("left", "Ratio")

        kd_values = [
            player["general"]["kills"]["count"] / (player["general"]["lost"]["count"] or 1)
            for player in self.stats
        ]

        kd_bar = LabeledBarGraphItem(
            categories=player_names,
            x=x_pos,
            height=kd_values,
            width=BAR_GROUP_WIDTH,
            brush="b",
            name="KD ratio",
        )
        kd_plot.addItem(kd_bar)
        kd_plot.getAxis("bottom").setTicks([[(i, name) for i, name in enumerate(player_names)]])

        line = pg.InfiniteLine(
            pos=1,
            angle=0,
            pen=pg.mkPen("r", style=pg.QtCore.Qt.PenStyle.DashLine),
        )
        kd_plot.addItem(line)
        return kd_plot

    def add_balance_plots(self) -> None:
        player_names = [player["name"] for player in self.stats]
        x_pos = np.arange(len(player_names))

        categories = ["mass", "energy", "count"]
        width = BAR_GROUP_WIDTH / len(categories)
        for index, category in enumerate(categories):
            plot = pg.PlotWidget(title=f"Build vs Loss ({category})")
            plot.addLegend()
            plot.setLabel("left", category)
            plot.setMinimumHeight(300)

            for i, (color, stat) in enumerate(zip(("b", "r", "g"), ("built", "lost", "kills"))):
                values = [player["general"][stat][category] for player in self.stats]
                bar = LabeledBarGraphItem(
                    categories=player_names,
                    x=x_pos + bar_shift(i, len(categories), width),
                    height=values,
                    width=width,
                    brush=color,
                    name=stat.title(),
                )
                plot.addItem(bar)
            plot.getAxis("bottom").setTicks(
                [[(i, name) for i, name in enumerate(player_names)]],
            )
            self.ui.balanceLayout.addWidget(plot, index // 2, index % 2)
        self.ui.balanceLayout.addWidget(self._create_kd_plot(), 1, 1)

    def add_score_plot(self) -> None:
        score_plot = pg.PlotWidget(title="Player Scores")
        score_plot.setLabel("left", "Score")

        player_names = [player["name"] for player in self.stats]
        player_scores = [player["general"]["score"] for player in self.stats]

        x_pos = np.arange(len(player_names))
        score_bar = LabeledBarGraphItem(
            categories=player_names,
            x=x_pos,
            height=player_scores,
            width=BAR_GROUP_WIDTH,
            brush=(0, 150, 255),
            name="Score",
        )
        score_plot.addItem(score_bar)
        score_plot.getAxis("bottom").setTicks([[(i, name) for i, name in enumerate(player_names)]])
        self.ui.scoreLayout.addWidget(score_plot)


class GameStatsUI:
    def _no_data(self) -> QLabel:
        label = QLabel("No game stats found")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = label.font()
        font.setBold(True)
        font.setPointSize(20)
        label.setFont(font)
        return label

    def setupUi(self, widget: QWidget) -> None:
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        self.stack.addWidget(self._no_data())


class GameStatsWidget(QWidget):
    def __init__(self) -> None:
        QWidget.__init__(self)
        self.ui = GameStatsUI()
        self.ui.setupUi(self)

    def initialize(self, replay: ReplayParser) -> None:
        self._remove_old_plots()
        self.draw_stats(replay.game_stats)

    def _remove_old_plots(self) -> None:
        while self.ui.stack.count() > 1:
            w = self.ui.stack.widget(1)
            assert w is not None
            self.ui.stack.removeWidget(w)
            w.deleteLater()

    def draw_stats(self, data: dict[str, GameStats]) -> None:
        if not data:
            return
        plots = PlotsWidget()
        self.ui.stack.addWidget(plots)
        plots.initialize(data)
        self.ui.stack.setCurrentIndex(1)
