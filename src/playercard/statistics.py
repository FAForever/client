from collections.abc import Generator
from collections.abc import Iterable

import numpy as np
import pyqtgraph as pg

from src.api.models.LeaderboardRating import LeaderboardRating
from src.api.models.PlayerEvent import PlayerEvent
from src.playercard.events import BUILT_LOST_METRICS
from src.playercard.events import EXPERIMENTALS_BUILT_LOST_METRICS
from src.playercard.events import FACTION_PLAYS_METRICS
from src.playercard.events import PlayerEventMetric
from src.qt.graphics.labeledbargraphitem import LabeledBarGraphItem
from src.qt.graphics.piechartitem import PieChartItem

BAR_GROUP_WIDTH = 0.8


class StatsCharts:
    def bar_chart(
            self,
            title: str,
            set_names: Iterable[str],
            metrics: tuple[PlayerEventMetric, ...],
            mapping: dict[str, PlayerEvent],
    ) -> pg.PlotWidget:
        plot = pg.PlotWidget(title=title)
        plot.addLegend()
        plot.setMinimumHeight(300)
        set0, set1, set2, categories = [], [], [], []
        for metric in metrics:
            value0, value1 = metric.get_components_values(mapping)
            set0.append(value0 + value1)
            set1.append(value0)
            set2.append(value1)
            categories.append(metric.name)
        x_pos = np.arange(len(categories))
        bar_width = BAR_GROUP_WIDTH / 3
        colors = ("b", "g", "r")
        sets = (set0, set1, set2)
        names = ("Total", *set_names)
        for i, (color, name, metric) in enumerate(zip(colors, names, sets)):
            bar = LabeledBarGraphItem(
                categories=categories,
                x=x_pos + (i - len(sets)/2 + 0.5) * bar_width,
                height=metric,
                width=bar_width,
                brush=color,
                name=name,
            )
            plot.addItem(bar)
        plot.getAxis("bottom").setTicks([[(i, name) for i, name in enumerate(categories)]])
        return plot

    def faction_won_lost(self, mapping: dict[str, PlayerEvent]) -> pg.PlotWidget:
        return self.bar_chart(
            "Games per faction",
            ("Wins", "Losses"),
            FACTION_PLAYS_METRICS,
            mapping,
        )

    def tech_built_lost(self, mapping: dict[str, PlayerEvent]) -> pg.PlotWidget:
        return self.bar_chart(
            "Units",
            ("Survived", "Lost"),
            BUILT_LOST_METRICS,
            mapping,
        )

    def exp_built_lost(self, mapping: dict[str, PlayerEvent]) -> pg.PlotWidget:
        return self.bar_chart(
            "Experimentals",
            ("Survived", "Lost"),
            EXPERIMENTALS_BUILT_LOST_METRICS,
            mapping,
        )

    def game_types_played(self, ratings: list[LeaderboardRating]) -> pg.PlotWidget:
        values = [rating.total_games for rating in ratings]
        labels = [
            rating.leaderboard.pretty_name
            for rating in ratings
            if rating.leaderboard is not None
        ]
        plot = pg.PlotWidget(title="Games played")
        plot.addLegend()
        plot.setMinimumHeight(300)
        pie = PieChartItem(values, labels, radius=100)
        plot.addItem(pie)
        plot.hideAxis("left")
        plot.hideAxis("bottom")
        plot.setRange(xRange=(-300, 300), yRange=(-100, 100))
        return plot

    def player_events_charts(
            self, events: list[PlayerEvent],
    ) -> Generator[pg.PlotWidget, None, None]:
        mapping = {
            player_event.event.xd: player_event
            for player_event in events
            if player_event.event is not None
        }
        yield self.faction_won_lost(mapping)
        yield self.tech_built_lost(mapping)
        yield self.exp_built_lost(mapping)
