from __future__ import annotations

from typing import cast

from PyQt6.QtCore import QEvent
from PyQt6.QtCore import QMetaObject
from PyQt6.QtCore import QObject
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QContextMenuEvent
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFormLayout
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QListWidget
from PyQt6.QtWidgets import QListWidgetItem
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src import fa
from src import util
from src.client.playercolors import PlayerColors
from src.client.user import UserRelations
from src.contextmenu.playercontextmenu import PlayerContextMenu
from src.fa.maps_.preview import create_largest_preview
from src.fa.maps_.previewdialog import MapPreviewDialog
from src.mapGenerator.mapgenManager import MapGeneratorManager
from src.model.game import Game
from src.model.game import GameState
from src.model.player import Player
from src.qt.widgets.clickablelabel import ClickableLabel


class TeamListEventFilter(QObject):
    def __init__(self, ctx_menu: PlayerContextMenu) -> None:
        super().__init__()
        self.ctx_menu = ctx_menu

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if event.type() is QEvent.Type.ContextMenu:
            self._handle_player_menu(
                cast(QListWidget, obj),
                cast(QContextMenuEvent, event),
            )
            return True
        else:
            return super().eventFilter(obj, event)

    def _handle_player_menu(self, widget: QListWidget, event: QContextMenuEvent) -> None:
        teamlist_item = widget.currentItem()
        if teamlist_item is None:
            return
        player = teamlist_item.data(Qt.ItemDataRole.UserRole)
        menu = self.ctx_menu.menu(player.login, player.id)
        menu.popup(event.globalPos())


class TeamWidgetUI:
    def setupUi(self, widget: QWidget) -> None:
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.teamList = QListWidget()
        self.teamList.setMaximumHeight(140)
        self.teamList.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.teamLabel = QLabel()
        self.numPlayersLabel = QLabel()
        self.teamRating = QLabel()
        line = QHBoxLayout()
        line.addWidget(self.teamLabel)
        line.addWidget(self.numPlayersLabel)
        line.addStretch()
        line.addWidget(self.teamRating)
        layout.addLayout(line)
        layout.addWidget(self.teamList)


class TeamWidget(QWidget):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.ui = TeamWidgetUI()
        self.ui.setupUi(self)
        self.ui.teamLabel.setText(name)

    def install_event_filter(self, event_filter: QObject) -> None:
        self.ui.teamList.installEventFilter(event_filter)

    def set_ratings(self, avg: float, total: int) -> None:
        self.ui.teamRating.setText(f"<b>Avg:</b> {avg:.0f} | <b>Total:</b> {total}")

    def set_num_players(self, num: int) -> None:
        self.ui.numPlayersLabel.setText(f"({num})")

    def add_player(self, player: Player, color: QColor) -> None:
        player_item = QListWidgetItem(f"{player.login} ({player.rating_estimate()})")
        if player.country is not None:
            country_icon = util.THEME.icon(f"chat/countries/{player.country.lower()}.png")
            player_item.setIcon(country_icon)
        player_item.setData(Qt.ItemDataRole.UserRole, player)
        player_item.setForeground(color)
        self.ui.teamList.addItem(player_item)

    def clear(self) -> None:
        self.ui.teamList.clear()


class GamePanelUI:
    def setupUi(self, widget: QWidget) -> None:
        layout = QVBoxLayout(widget)
        self.mapLabel = ClickableLabel()
        self.mapLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.getMapButton = QPushButton("Download/Generate map")

        self.titleLabel = QLabel()
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.titleLabel.setWordWrap(True)
        font = self.titleLabel.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 2)
        self.titleLabel.setFont(font)

        self.joinGameButton = QPushButton("Join Game")
        self.joinGameButton.setObjectName("joinGameButton")
        self.joinGameButton.hide()

        self.featuredModLabel = QLabel()

        self.mapNameLabel = QLabel()
        self.mapNameLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.hostLabel = QLabel()
        self.numPlayersLabel = QLabel()

        self.getMapButton.setEnabled(False)
        self.getMapButton.hide()

        layout.addWidget(self.mapLabel)
        layout.addWidget(self.getMapButton)
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.joinGameButton)

        self.summaryGroup = QGroupBox("Game Information")
        self.summaryGroup.hide()
        summary_form = QFormLayout(self.summaryGroup)
        summary_form.addRow("<b>Mod:</b>", self.featuredModLabel)
        summary_form.addRow("<b>Map:</b>", self.mapNameLabel)
        summary_form.addRow("<b>Host:</b>", self.hostLabel)
        summary_form.addRow("<b>Players:</b>", self.numPlayersLabel)
        layout.addWidget(self.summaryGroup)

        self.simModsButton = QPushButton("Show/Hide mods")
        self.simModsButton.hide()
        self.simModsList = QListWidget()
        self.simModsList.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.simModsList.setMaximumHeight(140)
        self.simModsList.hide()

        layout.addWidget(self.simModsButton)
        layout.addWidget(self.simModsList)

        self.teams: list[TeamWidget] = []
        for i in range(10):
            if i == 0:
                team = "<b>No team</b>"
            elif i == 9:
                team = "<b>Observers</b>"
            else:
                team = f"<b>Team {i}</b>"
            team_widget = TeamWidget(team)
            team_widget.hide()
            self.teams.append(team_widget)
            layout.addWidget(team_widget)
        layout.addStretch()


class GamePanelWidget(QWidget):
    join_requested = pyqtSignal(Game)

    def __init__(
        self,
        parent: QWidget,
        player_colors: PlayerColors,
        ctx_menu: PlayerContextMenu,
        user_relations: UserRelations,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("gamePanelWidget")
        self.player_colors = player_colors
        self.event_filter = TeamListEventFilter(ctx_menu)
        self.user_relations = user_relations
        self.user_relations.trackers.players.updated.connect(self.refresh_ui)
        self._mapgen_manager = MapGeneratorManager()
        self.ui = GamePanelUI()
        self.ui.setupUi(self)
        self.ui.simModsButton.clicked.connect(self.toggle_mods)
        self.ui.getMapButton.clicked.connect(self.get_map)
        self.ui.mapLabel.clicked.connect(self.show_large_map_preview)
        self.ui.joinGameButton.clicked.connect(self.join_game)
        self._mods_visible = False
        self.game: Game | None = None
        self.game_slot_conn: QMetaObject.Connection | None = None

        for team_widget in self.ui.teams:
            team_widget.install_event_filter(self.event_filter)

        self.setFixedWidth(290)

    def set_game(self, game: Game) -> None:
        if self.game is not None and self.game_slot_conn is not None:
            self.game.disconnect(self.game_slot_conn)
        self.game = game
        self.game_slot_conn = self.game.updated.connect(self.on_game_updated)
        self.ui.getMapButton.show()
        self.ui.joinGameButton.show()
        self.ui.summaryGroup.show()
        self.on_game_updated(game, game)

    def set_map_icon(self) -> None:
        if self.game is None:
            return
        pixmap = cast(QPixmap | None, fa.maps.preview(self.game.mapname, pixmap=True, large=True))
        if pixmap is None:
            self.ui.mapLabel.setPixmap(util.THEME.pixmap("games/unknown_map.png").scaled(256, 256))
        else:
            self.ui.mapLabel.setPixmap(pixmap)
        self.ui.getMapButton.setEnabled(not fa.maps.isMapAvailable(self.game.mapname))

    def refresh_ui(self) -> None:
        if self.game is None:
            return
        self.on_game_updated(self.game, self.game)

    def on_game_updated(self, new: Game, old: Game) -> None:
        if new.state is GameState.CLOSED:
            self.ui.joinGameButton.setText("Game Closed")
        elif new.state is GameState.PLAYING:
            self.ui.joinGameButton.setText("Game has Started")
        else:
            self.ui.joinGameButton.setText("Join Game")
        self.ui.joinGameButton.setEnabled(new.state is GameState.OPEN)
        self.set_map_icon()
        self.ui.titleLabel.setText(new.title)
        self.ui.titleLabel.setToolTip(new.title)
        if new.featured_mod != "faf":
            fmod_text = f"<font color='white'><b>{new.featured_mod}</b></font>"
            self.ui.featuredModLabel.setText(fmod_text)
        else:
            self.ui.featuredModLabel.setText(new.featured_mod)
        host = new.to_player(new.host)
        if host is not None:
            color = self.player_colors.get_user_color(host.id)
            self.ui.hostLabel.setText(f"<font color='{color}'>{new.host}</font>")
        else:
            self.ui.hostLabel.setText(new.host)
        self.ui.mapNameLabel.setText(new.mapname)
        self.ui.mapNameLabel.setToolTip(new.mapname)
        self.ui.numPlayersLabel.setText(f"{len(new.playing_players)}/{new.max_players}")
        self.update_sim_mods()
        self.update_teams()

    def update_sim_mods(self) -> None:
        if self.game is None or not self.game.sim_mods:
            self.ui.simModsButton.hide()
            self.ui.simModsList.hide()
            return
        self.ui.simModsButton.show()
        self.ui.simModsList.setVisible(self._mods_visible)
        self.ui.simModsList.clear()
        self.ui.simModsList.addItems(sorted(self.game.sim_mods.values()))

    def update_teams(self) -> None:
        if self.game is None:
            return
        for team_widget in self.ui.teams:
            team_widget.hide()

        for team, logins in self.game.playing_teams.items():
            team_widget = self.ui.teams[int(team) - 1]
            team_widget.clear()
            total_rating = 0
            for login in logins:
                player = self.game.to_player(login)
                if player is None:
                    continue
                if login == self.game.host:
                    color = QColor(self.player_colors.get_color("game_host"))
                else:
                    color = QColor(self.player_colors.get_user_color(player.id))
                team_widget.add_player(player, color)
                total_rating += player.rating_estimate()

            average_rating = total_rating / len(logins) if len(logins) > 0 else 0
            team_widget.set_ratings(average_rating, total_rating)
            team_widget.set_num_players(len(logins))
            team_widget.show()

        observers_widget = self.ui.teams[-1]
        if observers := self.game.observers:
            observers_widget.clear()
            for login in observers:
                player = self.game.to_player(login)
                if player is None:
                    continue
                color = QColor(self.player_colors.get_user_color(player.id))
                observers_widget.add_player(player, color)
            observers_widget.set_num_players(len(observers))
            observers_widget.show()
        else:
            observers_widget.hide()

    def toggle_mods(self) -> None:
        self._mods_visible = not self._mods_visible
        self.ui.simModsList.setVisible(self._mods_visible)

    def get_map(self) -> None:
        if self.game is None:
            return
        if fa.maps.isGeneratedMap(self.game.mapname):
            self._mapgen_manager.generateMap(self.game.mapname)
        else:
            fa.maps.downloadMap(self.game.mapname)
        self.set_map_icon()

    def show_large_map_preview(self) -> None:
        if self.game is None or (map_folder := fa.maps.folderForMap(self.game.mapname)) is None:
            return
        pixmap = create_largest_preview(self.screen(), map_folder)
        preview_dialog = MapPreviewDialog(pixmap, cast(QWidget, self.parent()))
        preview_dialog.exec()
        preview_dialog.deleteLater()

    def join_game(self) -> None:
        if self.game is None:
            return
        self.join_requested.emit(self.game)
