from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from typing import cast

from PyQt6.QtCore import QModelIndex
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLayout
from PyQt6.QtWidgets import QListView
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.api.models.Game import Game
from src.contextmenu.playercontextmenu import PlayerContextMenu
from src.replays.models import ScoreboardModel
from src.replays.models import ScoreboardModelItem
from src.replays.scoreboarditemdelegate import ScoreboardItemDelegate
from src.replays.scoreboardlistview import ScoreboardListView


class GameResult(Enum):
    WIN = "Win"
    LOSE = "Lose"
    PLAYING = "Playing"
    UNKNOWN = "???"


class Scoreboard(QWidget):
    GAME_RESULT_RESERVED_HEIGHT = 30
    TITLE_RESERVED_HEIGHT = 30
    VALIDITY_RESERVED_HEIGHT = 20

    def __init__(
            self,
            mod: str | None,
            winner: dict | None,
            spoiled: bool,
            duration: str | None,
            teamwin: dict | None,
            uid: str,
            teams: dict,
            player_menu_handler: PlayerContextMenu,
            game: Game,
    ) -> None:
        super().__init__()
        self.winner = winner
        self.spoiled = spoiled
        self.duration = duration or ""
        self.teamwin = teamwin
        self.uid = uid
        self.teams = teams
        self.num_teams = len(self.teams)
        self.biggest_team = max(len(team) for team in self.teams.values()) if self.teams else 0
        self.player_menu_handler = player_menu_handler
        self.game = game

        self.main_layout = QVBoxLayout()
        self.teams_layout = self._get_teams_layout(self.num_teams)
        self.setLayout(self.main_layout)
        self.mod = mod
        self._height = 0
        self._team_heights: list[int] = []

    def _get_teams_layout(self, num_teams: int) -> QVBoxLayout | QHBoxLayout:
        if num_teams == 2:
            return QHBoxLayout()
        return QVBoxLayout()

    def create_teamlist_view(self) -> ScoreboardListView:
        team_view = ScoreboardListView()
        team_view.setObjectName("replayScoreTeamList")
        return team_view

    def _create_team_result_label(self, text: str) -> QLabel:
        result_label = QLabel(text)
        result_label.setObjectName("replayGameResult")
        result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        font = result_label.font()
        font.setPointSize(font.pointSize() + 4)
        result_label.setFont(font)

        return result_label

    def add_result_label(self, text: str, layout: QLayout) -> None:
        result_label = self._create_team_result_label(text)
        layout.addWidget(result_label)

    def teamview_rows(self, view: QListView) -> int:
        model = cast(ScoreboardModel, view.model())
        if self.num_teams == 2:
            return self.biggest_team
        return model.rowCount(QModelIndex())

    def teamview_height(self, view: QListView) -> int:
        row_count = self.teamview_rows(view)
        delegate = cast(ScoreboardItemDelegate, view.itemDelegate())
        return row_count * delegate.row_height()

    def adjust_teamview_height(self, view: QListView, height: int) -> None:
        view.setMinimumHeight(height)
        view.setMaximumHeight(height)

    def add_team_score(
            self,
            alignment: Qt.AlignmentFlag,
            team_result: GameResult,
            players: Iterable[dict],
    ) -> None:
        team_layout = QVBoxLayout()
        self.add_result_label(team_result.value, team_layout)

        model = ScoreboardModel(self.spoiled, alignment, ScoreboardModelItem.builder(self.mod))
        for player in players:
            model.add_player(player)

        team_view = self.create_teamlist_view()
        team_view.setModel(model)
        team_view.setItemDelegate(ScoreboardItemDelegate())
        team_view.set_menu_handler(self.player_menu_handler)
        team_layout.addWidget(team_view)

        view_height = self.teamview_height(team_view)
        self.adjust_teamview_height(team_view, view_height)
        self._team_heights.append(self.GAME_RESULT_RESERVED_HEIGHT + view_height)

        self.teams_layout.addLayout(team_layout)

    def add_team_score_if_needed(
            self,
            alignment: Qt.AlignmentFlag,
            team_result: GameResult,
            players: Iterable[dict],
    ) -> None:
        if len(list(players)) == 0:
            return
        self.add_team_score(alignment, team_result, players)

    def height(self) -> int:
        # there must be a way to dissect all of the layouts and widgets
        # with all of their paddings, spacings, margins etc. to determine
        # scoreboard's precise height, but this works good enough
        magic = 50
        if len(self.teams) == 2:
            return self._height + max(self._team_heights) + magic
        return sum((self._height, *self._team_heights, magic))

    def width(self) -> int:
        if len(self.teams) == 2:
            return 560 if self.spoiled else 500
        return 335 if self.spoiled else 275

    def one_team_layout(self) -> None:
        team = list(self.teams.values())[0]
        alignment = Qt.AlignmentFlag.AlignLeft
        if self.spoiled:
            winners, losers = [], []
            for player in team:
                if self.winner is not None and player["score"] == self.winner["score"]:
                    winners.append(player)
                else:
                    losers.append(player)
            self.add_team_score_if_needed(alignment, self.game_result(is_winner=True), winners)
            self.add_team_score_if_needed(alignment, self.game_result(is_winner=False), losers)
        else:
            self.add_team_score_if_needed(alignment, self.game_result(is_winner=False), team)
        self.main_layout.addLayout(self.teams_layout)

    def default_layout(self) -> None:
        alignment = Qt.AlignmentFlag.AlignLeft
        for team in self.teams:
            game_result = self.game_result(is_winner=(team == self.teamwin))
            self.add_team_score(alignment, game_result, self.teams[team])
        self.main_layout.addLayout(self.teams_layout)

    def game_result(self, *, is_winner: bool) -> GameResult:
        if not self.spoiled:
            return GameResult.UNKNOWN
        if "playing" in self.duration:
            return GameResult.PLAYING
        return (GameResult.LOSE, GameResult.WIN)[is_winner]

    def two_teams_layout(self) -> None:
        for index, team_num in enumerate(self.teams):
            alignment = (Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignRight)[index]
            is_winner = team_num == self.teamwin
            game_result = self.game_result(is_winner=is_winner)
            self.add_team_score(alignment, game_result, self.teams[team_num])
            if index == 0:
                self.add_vs_label()
        self.main_layout.addLayout(self.teams_layout)

    def create_title_label(self) -> QLabel:
        title_label = QLabel(f"Replay UID: {self.uid}")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        title_font = title_label.font()
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        title_label.setFont(title_font)

        return title_label

    def add_title_label(self) -> None:
        self.main_layout.addWidget(self.create_title_label())
        self._height += self.TITLE_RESERVED_HEIGHT

    def create_vs_label(self) -> QLabel:
        vs_label = QLabel("VS")
        vs_label.setObjectName("VSLabel")
        vs_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        font = vs_label.font()
        font.setPointSize(font.pointSize() + 13)
        vs_label.setFont(font)

        return vs_label

    def add_vs_label(self) -> None:
        self.teams_layout.addWidget(self.create_vs_label())

    def add_validity(self) -> None:
        layout = QHBoxLayout()

        victory_condition = QLabel(f"{self.game.victory_condition}")
        victory_condition.setProperty("replay_misc_info", "true")
        victory_condition.setToolTip("Victory Condition")

        validity = QLabel(f"{self.game.validity}")
        validity.setProperty("replay_misc_info", "true")
        validity.setToolTip("Validity")

        layout.addStretch()
        layout.addWidget(victory_condition)
        layout.addWidget(validity)
        layout.addStretch()

        self.main_layout.addLayout(layout)
        self._height += self.VALIDITY_RESERVED_HEIGHT

    def setup(self) -> None:
        self.add_title_label()
        self.add_validity()

        if self.num_teams == 1:
            self.one_team_layout()
        elif self.num_teams == 2:
            self.two_teams_layout()
        else:
            self.default_layout()
