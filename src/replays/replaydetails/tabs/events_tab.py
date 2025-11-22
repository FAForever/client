from __future__ import annotations

import enum
import re
from collections.abc import Sequence
from dataclasses import dataclass
from operator import itemgetter
from typing import Self
from typing import cast

from PyQt6.QtCore import QModelIndex
from PyQt6.QtCore import QPoint
from PyQt6.QtCore import QRect
from PyQt6.QtCore import QRectF
from PyQt6.QtCore import QSize
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QIcon
from PyQt6.QtGui import QPainter
from PyQt6.QtGui import QPainterPath
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QButtonGroup
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QListView
from PyQt6.QtWidgets import QStyleOptionViewItem
from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.config import Settings
from src.fa.factions import Factions
from src.qt.itemviews.styleditemdelegate import StyledItemDelegate
from src.qt.models.qtlistmodel import QtListModel
from src.qt.models.qtlistmodel import QtListModelItem
from src.qt.utils import block_signals
from src.qt.utils import qpainter
from src.replays.replaydetails.chatnotifiers import ACU_BLUEPRINTS
from src.replays.replaydetails.chatnotifiers import ACU_UPGRADE_NOTIFIERS
from src.replays.replaydetails.chatnotifiers import UNIT_NOTIFIERS
from src.replays.replaydetails.helpers import seconds_to_human
from src.replays.replaydetails.pixmaps import enhancement_pixmap
from src.replays.replaydetails.pixmaps import units_pixmaps
from src.replays.replaydetails.replayreader import ReplayParser
from src.replays.replaydetails.utils import PLAYER_COLORS


class EventType(enum.Enum):
    ACU_UPGRADE = enum.auto()
    HQ_UPGRADE = enum.auto()
    UNIT = enum.auto()
    LAST_COMMAND = enum.auto()


@dataclass(frozen=True)
class EventNotice:
    typ: EventType
    picture_name: str


@dataclass(frozen=True)
class ReplayEvent(EventNotice):
    tick: int
    login: str
    description: str
    faction: str
    color: str
    team: float
    sender: int


class EventModelItem(QtListModelItem):
    def __init__(self, replay_event: ReplayEvent) -> None:
        super().__init__()
        self.replay_event = replay_event

    @classmethod
    def make(cls, replay_event: ReplayEvent) -> Self:
        return cls(replay_event)

    def pixmap(self) -> QPixmap:
        if self.replay_event.typ is EventType.ACU_UPGRADE:
            return enhancement_pixmap(self.replay_event.faction, self.replay_event.picture_name)
        else:
            return units_pixmaps()[self.replay_event.picture_name]

    def tooltip(self) -> str:
        return f"{self.replay_event.description}\n[{self.replay_event.login}]"


class ReplayEventModel(QtListModel[ReplayEvent, EventModelItem]):
    def __init__(self) -> None:
        super().__init__(EventModelItem.make)
        self._id_counter = 0

    def add_replay_event(self, data: ReplayEvent) -> None:
        self._add_item(data, self._id_counter)
        self._id_counter += 1

    def clear_replay_events(self) -> None:
        self._clear_items()
        self._id_counter = 0


class EventItemDelegate(StyledItemDelegate):
    def __init__(self, *, render_teams: bool) -> None:
        super().__init__()
        self.render_teams = render_teams

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(76, 100)

    def paint(
        self,
        painter: QPainter | None,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        if painter is None:
            return
        event_item: EventModelItem = index.data()
        with qpainter(painter) as p:
            self._draw_background(p, option.rect, event_item)
            self._draw_clear_option(p, option)
            self._draw_icon(p, option.rect, event_item)
            self._draw_text(p, option.rect, event_item)

            if self.render_teams:
                self._draw_team(p, option.rect, event_item)

    def _draw_background(
        self,
        painter: QPainter,
        item_rect: QRect,
        model_item: EventModelItem,
    ) -> None:
        path = QPainterPath()
        path.addRoundedRect(QRectF(item_rect), 3, 3)
        painter.fillPath(path, QColor(model_item.replay_event.color))

    def _draw_icon(
        self,
        painter: QPainter,
        item_rect: QRect,
        model_item: EventModelItem,
    ) -> None:
        pix_size = 64
        icon = QIcon(model_item.pixmap())
        icon_rect = QRect(item_rect)
        icon_rect.setSize(QSize(pix_size, pix_size))
        item_center = item_rect.center()
        icon_rect.moveCenter(QPoint(item_center.x(), item_rect.top() + pix_size // 2 + 6))
        icon.paint(painter, icon_rect)

    def _draw_text(
        self,
        painter: QPainter,
        item_rect: QRect,
        model_item: EventModelItem,
    ) -> None:
        text_rect = QRect(item_rect)
        text_rect.setHeight(20)
        text_rect.setWidth(56)
        text_rect.moveCenter(QPoint(item_rect.center().x(), item_rect.bottom() - 16))
        path = QPainterPath()
        path.addRoundedRect(QRectF(text_rect), 4, 4)
        painter.fillPath(path, QColor("#202025"))

        text = str(seconds_to_human(model_item.replay_event.tick // 10))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_team(
        self,
        painter: QPainter,
        item_rect: QRect,
        model_item: EventModelItem,
    ) -> None:
        team_rect = QRect(item_rect.right() - 11, item_rect.y() + 1, 10, 10)

        path = QPainterPath()
        path.addRoundedRect(QRectF(team_rect), 2, 2)

        font = painter.font()
        font.setPointSize(font.pointSize() - 2)
        painter.setFont(font)
        painter.fillPath(path, QColor("#202025"))
        text = f"{model_item.replay_event.team - 1:.0f}"
        painter.drawText(team_rect, Qt.AlignmentFlag.AlignCenter, text)


class EventsTabUI:
    def setupUi(self, widget: QWidget) -> None:
        self.showTeamsCheckBox = QCheckBox("Render team numbers")

        layout = QHBoxLayout(widget)
        self.eventsList = QListView()
        self.eventsList.setSpacing(2)
        self.eventsList.setObjectName("replayEvents")
        self.eventsList.setFlow(QListView.Flow.LeftToRight)
        self.eventsList.setResizeMode(QListView.ResizeMode.Adjust)
        self.eventsList.setWrapping(True)
        self.eventsList.setUniformItemSizes(True)
        self.eventsList.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        layout.addWidget(self.eventsList, 3)

        settings_layout = QVBoxLayout()
        self.filter_tab_widget = QTabWidget(widget)

        self.filter_upgrades_widget = QWidget()
        self.filter_upgrades_widget.setObjectName("overview_widget")

        self.filter_players_widget = QWidget()
        self.filter_players_widget.setObjectName("overview_widget")

        self.filter_tab_widget.addTab(self.filter_upgrades_widget, "Upgrades")
        self.filter_tab_widget.addTab(self.filter_players_widget, "Players")

        self.filterUpgradesLayout = QVBoxLayout(self.filter_upgrades_widget)

        self.selectAllUpgradesCheckBox = QCheckBox("Select All")

        self.acuUpgradesCheckBox = QCheckBox("ACU Upgrade")
        self.factoryUpgradesCheckBox = QCheckBox("HQ Upgrade")
        self.expCheckBox = QCheckBox("Experimental / Arty / Nuke")
        self.lastCommandCheckBox = QCheckBox("Approximate Death (Last Command)")

        for btn in (
            self.selectAllUpgradesCheckBox,
            self.acuUpgradesCheckBox,
            self.factoryUpgradesCheckBox,
            self.expCheckBox,
            self.lastCommandCheckBox,
        ):
            btn.setChecked(True)

        self.filterUpgradesLayout.addWidget(self.selectAllUpgradesCheckBox)
        self.filterUpgradesLayout.addSpacing(6)
        self.filterUpgradesLayout.addWidget(self.acuUpgradesCheckBox)
        self.filterUpgradesLayout.addWidget(self.factoryUpgradesCheckBox)
        self.filterUpgradesLayout.addWidget(self.expCheckBox)
        self.filterUpgradesLayout.addWidget(self.lastCommandCheckBox)
        self.filterUpgradesLayout.addStretch()

        self.filterPlayersLayout = QVBoxLayout(self.filter_players_widget)

        self.selectAllPlayersCheckBox = QCheckBox("Select All")
        self.selectAllPlayersCheckBox.setChecked(True)

        self.filterPlayersLayout.addWidget(self.selectAllPlayersCheckBox)
        self.filterPlayersLayout.addSpacing(6)

        settings_layout.addWidget(self.showTeamsCheckBox)
        settings_layout.addWidget(self.filter_tab_widget)
        layout.addLayout(settings_layout, 1)


class EventsTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.ui = EventsTabUI()
        self.ui.setupUi(self)
        self.finished_pattern = re.compile(r"(.+) (done!|готов!)(.+\(.+\))?")

        self.visible_upgrades = Settings.get_list(
            "replaycard.events/visible_upgrades",
            default=[True] * (len(tuple(EventType)) + 1),  # +1 for 'Select All' checkbox
            type=bool,
        )
        self.ui.selectAllUpgradesCheckBox.setChecked(all(self.visible_upgrades[1:]))

        self.upgrade_filter_group = QButtonGroup()
        self.upgrade_filter_group.setExclusive(False)
        for i, btn in enumerate((
            self.ui.selectAllUpgradesCheckBox,
            self.ui.acuUpgradesCheckBox,
            self.ui.factoryUpgradesCheckBox,
            self.ui.expCheckBox,
            self.ui.lastCommandCheckBox,
        )):
            self.upgrade_filter_group.addButton(btn, i)
            if i != 0:
                btn.setChecked(self.visible_upgrades[i])
        self.upgrade_filter_group.buttonToggled.connect(self.on_upgrade_filter_changed)

        self.players_filter_group = QButtonGroup()
        self.players_filter_group.setExclusive(False)
        self.players_filter_group.addButton(self.ui.selectAllPlayersCheckBox)
        self.players_filter_group.buttonToggled.connect(self.on_player_filter_changed)

        self.armies: dict[int, dict[str, str | float]] = {}
        self.players: dict[int, str] = {}
        self.chat_lines: Sequence[tuple[int, str, str, str, int]] = ()
        self.last_activity: dict[int, int] = {}

        render_teams = Settings.get("replaycard.events/render_teams", default=False, type=bool)
        self.ui.showTeamsCheckBox.setChecked(render_teams)
        self.ui.showTeamsCheckBox.checkStateChanged.connect(self.on_show_teams_changed)

        self.events_model = ReplayEventModel()
        self.events_item_delegate = EventItemDelegate(render_teams=render_teams)
        self.ui.eventsList.setModel(self.events_model)
        self.ui.eventsList.setItemDelegate(self.events_item_delegate)

    def on_upgrade_filter_changed(self, button: QCheckBox) -> None:
        if button is self.ui.selectAllUpgradesCheckBox:
            with block_signals(self.upgrade_filter_group) as group:
                for btn in group.buttons():
                    btn.setChecked(button.isChecked())
        elif self.ui.selectAllUpgradesCheckBox.isChecked():
            with block_signals(self.upgrade_filter_group):
                self.ui.selectAllUpgradesCheckBox.setChecked(False)

        self.visible_upgrades = [btn.isChecked() for btn in self.upgrade_filter_group.buttons()]
        self.update_visibility()

    def on_player_filter_changed(self, button: QCheckBox) -> None:
        if button is self.ui.selectAllPlayersCheckBox:
            with block_signals(self.players_filter_group) as group:
                for btn in group.buttons():
                    btn.setChecked(button.isChecked())
        elif self.ui.selectAllPlayersCheckBox.isChecked():
            with block_signals(self.players_filter_group):
                self.ui.selectAllPlayersCheckBox.setChecked(False)

        self.update_visibility()

    def update_visibility(self) -> None:
        for row in range(self.events_model.rowCount()):
            model_index = self.events_model.index(row)
            model_item = cast(
                EventModelItem,
                self.events_model.data(model_index, Qt.ItemDataRole.DisplayRole),
            )
            player_btn = self.players_filter_group.button(model_item.replay_event.sender)
            assert player_btn is not None

            event_btn = self.upgrade_filter_group.button(model_item.replay_event.typ.value)
            assert event_btn is not None

            hide = not player_btn.isChecked() or not event_btn.isChecked()
            self.ui.eventsList.setRowHidden(row, hide)

    def identify_notice(self, faction: str, desc: str) -> EventNotice | None:
        try:
            ret, _ = ACU_UPGRADE_NOTIFIERS[faction][desc]
            return EventNotice(EventType.ACU_UPGRADE, ret)
        except KeyError:
            pass
        try:
            ret = UNIT_NOTIFIERS[faction][desc]
            return EventNotice(EventType.UNIT if "230" in ret else EventType.HQ_UPGRADE, ret)
        except KeyError:
            pass
        try:
            return EventNotice(EventType.UNIT, UNIT_NOTIFIERS["experimentals"][desc])
        except KeyError:
            return None

    def initialize(self, parser: ReplayParser) -> None:
        self.armies = parser.army
        self.players = parser.players
        self.chat_lines = parser.chatLine
        self.last_activity = parser.last_activity
        self.teams = parser.teams

        self.clear()
        self.add_events()
        self.add_player_checkboxes()

    def clear(self) -> None:
        self.events_model.clear_replay_events()
        while (layout_item := self.ui.filterPlayersLayout.takeAt(2)) is not None:
            if (player_line_layout := layout_item.layout()) is None:
                continue
            while (line_item := player_line_layout.takeAt(0)) is not None:
                if (widget := line_item.widget()) is not None:
                    widget.deleteLater()
        for button in self.players_filter_group.buttons():
            if button is self.ui.selectAllPlayersCheckBox:
                continue
            self.players_filter_group.removeButton(button)

    def add_events(self) -> None:
        sorted_last_coms = sorted(self.last_activity.items(), key=itemgetter(1))

        events_gen = (line for line in self.chat_lines if line[2] == "notify")
        for tick, *_, text, sender in events_gen:
            if not (found := self.finished_pattern.match(text)):
                continue

            # ACU death/last command is not present in chat notifications
            if sorted_last_coms and sorted_last_coms[0][1] <= tick:
                dead_army, death_tick = sorted_last_coms.pop(0)
                faction = Factions(self.armies[dead_army]["Faction"]).name.lower()
                unit = ACU_BLUEPRINTS[faction]
                self.events_model.add_replay_event(
                    ReplayEvent(
                        EventType.LAST_COMMAND,
                        unit,
                        death_tick,
                        cast(str, self.armies[dead_army]["PlayerName"]),
                        "Last Command",
                        faction,
                        PLAYER_COLORS[int(self.armies[dead_army]["PlayerColor"]) - 1],
                        cast(float, self.armies[dead_army]["Team"]),
                        dead_army,
                    ),
                )

            faction = Factions(self.armies[sender]["Faction"]).name.lower()
            enh_name = found[1].strip()

            notice = self.identify_notice(faction, enh_name.replace("upgrade", "").strip())
            if notice is None:
                continue
            color = PLAYER_COLORS[int(self.armies[sender]["PlayerColor"]) - 1]
            login = cast(str, self.armies[sender]["PlayerName"])
            team = cast(float, self.armies[sender]["Team"])
            replay_event = ReplayEvent(
                notice.typ,
                notice.picture_name,
                tick,
                login,
                f"{enh_name}{found[3] or ''}",
                faction,
                color,
                team,
                sender,
            )
            self.events_model.add_replay_event(replay_event)

    def add_player_checkboxes(self) -> None:
        if len(self.players) == len(self.teams):
            for army_id in self.players:
                self._add_player_checkbox(army_id)
        else:
            for _, players in self.teams.items():
                for army_id in players:
                    self._add_player_checkbox(army_id)
                self.ui.filterPlayersLayout.addSpacing(12)

        self.ui.filterPlayersLayout.addStretch()

    def _add_player_checkbox(self, army_id: int) -> None:
        line = QHBoxLayout()

        checkbox = QCheckBox(cast(str, self.armies[army_id]["PlayerName"]))
        checkbox.setChecked(True)

        color_label = QLabel()
        color_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        color_label.setMaximumSize(10, 10)

        color_pixmap = QPixmap(10, 10)
        color_pixmap.fill(QColor(PLAYER_COLORS[int(self.armies[army_id]["PlayerColor"]) - 1]))
        color_label.setPixmap(color_pixmap)

        line.addWidget(checkbox)
        line.addWidget(color_label)
        line.addStretch()

        self.ui.filterPlayersLayout.addLayout(line)
        self.players_filter_group.addButton(checkbox, army_id)

    def save_settings(self) -> None:
        Settings.set(
            "replaycard.events/visible_upgrades",
            self.visible_upgrades,
        )
        Settings.set("replaycard.events/render_teams", self.events_item_delegate.render_teams)

    def on_show_teams_changed(self, state: Qt.CheckState) -> None:
        self.events_item_delegate.render_teams = state == Qt.CheckState.Checked
        self.ui.eventsList.update()
