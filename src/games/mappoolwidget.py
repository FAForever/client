from collections import Counter
from math import inf
from typing import Literal
from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QFrame
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.api.models.Map import Map
from src.api.models.MapPoolAssignment import MapPoolAssignment
from src.api.models.MapVersion import Map as HackyMap
from src.api.models.MapVersion import MapVersion
from src.api.models.MatchmakerQueueMapPool import MatchmakerQueueMapPool
from src.api.vaults_api import MapPoolApiConnector
from src.fa import maps
from src.model.player import Player
from src.qt.widgets.clickablelabel import ClickableLabel
from src.vaults.dialogs import show_item_details_dialog
from src.vaults.mapvault.mapdetails import MapDetailsWidget


class TokenTracker:
    def __init__(self, total: int, per_map: int, counter: Counter[str]) -> None:
        self.total = total
        self.per_map = per_map
        self.counter = counter

    def __getitem__(self, xd: str, /) -> int:
        return self.counter[xd]

    @property
    def used(self) -> int:
        return self.counter.total()

    @property
    def remaining(self) -> int:
        return self.total - self.used

    def reset_tokens(self) -> None:
        self.counter.clear()

    def add(self, xd: str) -> None:
        self.counter[xd] += 1

    def remove(self, xd: str) -> None:
        self.counter[xd] -= 1

    def can_add(self, xd: str) -> bool:
        return self.used < self.total and self.counter[xd] < self.per_map

    def can_remove(self, xd: str) -> bool:
        return self.counter[xd] > 0


class MapCardUI:
    ICON_WIDTH = 128
    SPACING = 6

    def setupUi(self, widget: QWidget) -> None:
        main_layout = QGridLayout(widget)
        main_layout.setSpacing(self.SPACING)

        self.mapIconLabel = ClickableLabel()
        self.mapIconLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mapIconLabel.setObjectName("vetoMapIcon")

        self.mapNameLabel = QLabel()
        self.mapNameLabel.setWordWrap(True)
        self.mapNameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mapNameLabel.setMaximumWidth(self.ICON_WIDTH)
        self.mapNameLabel.setObjectName("iconOverlay")

        token_widget = QWidget()
        token_widget.setMaximumWidth(self.ICON_WIDTH)
        token_layout = QHBoxLayout(token_widget)
        token_layout.setContentsMargins(0, 0, 0, 0)

        self.tokensAppliedLabel = QLabel()
        self.tokensAppliedLabel.setObjectName("vetoTokens")
        self.tokensAppliedLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.addTokenButton = QPushButton("+")
        self.addTokenButton.setObjectName("vetoButton")

        self.removeTokenButton = QPushButton("-")
        self.removeTokenButton.setObjectName("vetoButton")
        self.removeTokenButton.setEnabled(False)

        token_layout.addWidget(self.removeTokenButton)
        token_layout.addWidget(self.tokensAppliedLabel)
        token_layout.addWidget(self.addTokenButton)

        self.numSpawnsLabel = QLabel()
        self.numSpawnsLabel.setObjectName("iconOverlay")

        self.headerWidget = QWidget()
        self.headerWidget.setMaximumWidth(self.ICON_WIDTH)
        header_layout = QHBoxLayout(self.headerWidget)
        header_layout.setSpacing(0)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(self.numSpawnsLabel)

        self.mapSizeLabel = QLabel()
        self.mapSizeLabel.setObjectName("iconOverlay")
        self.mapSizeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.footerWidget = QWidget()
        self.footerWidget.setMaximumWidth(self.ICON_WIDTH)
        footer_layout = QVBoxLayout(self.footerWidget)
        footer_layout.setSpacing(0)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(self.mapNameLabel)
        footer_layout.addWidget(self.mapSizeLabel)

        self.vetoOverlayLabel = QLabel("BANNED")
        self.vetoOverlayLabel.setObjectName("vetoOverlay")
        self.vetoOverlayLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vetoOverlayLabel.setMaximumWidth(self.ICON_WIDTH)
        self.vetoOverlayLabel.hide()

        main_layout.addWidget(self.mapIconLabel, 0, 0)
        main_layout.addWidget(self.headerWidget, 0, 0, alignment=Qt.AlignmentFlag.AlignTop)
        main_layout.addWidget(self.footerWidget, 0, 0, alignment=Qt.AlignmentFlag.AlignBottom)
        main_layout.addWidget(self.vetoOverlayLabel, 0, 0)
        main_layout.addWidget(token_widget, 1, 0)


class MapCard(QFrame):
    tokens_changed = pyqtSignal()
    map_clicked = pyqtSignal(HackyMap)

    def __init__(
        self,
        assignment: MapPoolAssignment,
        tokens: TokenTracker,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("vetoFrame")
        self.setContentsMargins(0, 0, 0, 0)
        self.ui = MapCardUI()
        self.ui.setupUi(self)

        self.ui.addTokenButton.clicked.connect(self.add_token)
        self.ui.removeTokenButton.clicked.connect(self.remove_token)

        self.assignment = assignment
        self.xd = assignment.xd

        if assignment.map_params is not None:
            self.map = assignment.map_params.to_map()
            self.map_version = cast(MapVersion, self.map.version)
        elif assignment.map_version is not None:
            self.map_version = assignment.map_version
            assert self.map_version.map is not None
            self.map = self.map_version.map
            self.map.version = self.map_version
        else:
            raise
        self.map_name = self.map.display_name

        self.tokens = tokens

    def mousePressEvent(self, ev: QMouseEvent | None) -> None:  # type: ignore[override]
        if (
            ev is None
            or self.assignment.map_version is None
            or ev.position().y() > self.ui.ICON_WIDTH + self.ui.SPACING
        ):
            return
        self.map_clicked.emit(self.map)

    def fill_ui(self) -> None:
        self.ui.mapNameLabel.setText(f"<b>{self.map_name}</b>")

        # FIXME: get rid of cast
        pixmap = cast(QPixmap | None, maps.preview(self.map_version.folder_name, pixmap=True))
        if pixmap is not None:
            scaled = pixmap.scaled(
                self.ui.ICON_WIDTH,
                self.ui.ICON_WIDTH,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.ui.mapIconLabel.setPixmap(scaled)

        self.ui.numSpawnsLabel.setText(f"Spawns: {self.map_version.max_players}")
        self.ui.numSpawnsLabel.setVisible(self.assignment.map_params is not None)

        width = self.map_version.size.width_km
        height = self.map_version.size.height_km
        self.ui.mapSizeLabel.setText(
            f"{width:.{int(not width.is_integer())}f}km x "
            f"{height:.{int(not height.is_integer())}f}km",
        )
        self.update_appearance()

    def add_token(self) -> None:
        if self.tokens.can_add(self.xd):
            self.tokens.add(self.xd)
            self.tokens_changed.emit()

    def remove_token(self) -> None:
        if self.tokens[self.xd] > 0:
            self.tokens.remove(self.xd)
            self.tokens_changed.emit()

    def update_appearance(self) -> None:
        self.ui.addTokenButton.setEnabled(self.tokens.can_add(self.xd))
        self.ui.removeTokenButton.setEnabled(self.tokens.can_remove(self.xd))
        if (applied := self.tokens[self.xd]) > 0:
            self.ui.tokensAppliedLabel.setText(f"🛇 {applied}")
        else:
            self.ui.tokensAppliedLabel.clear()
        self.ui.vetoOverlayLabel.setVisible(applied == self.tokens.per_map)
        for widget in (self.ui.mapIconLabel, self.ui.headerWidget, self.ui.footerWidget):
            widget.setEnabled(applied != self.tokens.per_map)


class MapPoolWidgetUI:
    def setupUi(self, widget: QWidget) -> None:
        main_layout = QVBoxLayout(widget)
        info_layout = QHBoxLayout()

        self.bracketComboBox = QComboBox()

        self.totalCapLabel = QLabel()
        counter_font = QFont()
        counter_font.setPointSize(12)
        self.totalCapLabel.setFont(counter_font)

        self.clearTokensButton = QPushButton("Clear tokens")
        self.mapCapLabel = QLabel()
        self.mapCapLabel.setFont(counter_font)

        scroll = QScrollArea()
        scroll.setObjectName("mapPoolWidgetScrollArea")
        scroll.setWidgetResizable(True)

        map_container = QWidget()
        map_container.setObjectName("overview_widget")
        self.mapCardsLayout = QGridLayout(map_container)
        self.mapCardsLayout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(map_container)

        info_layout.addWidget(self.clearTokensButton)
        info_layout.addStretch()
        info_layout.addWidget(self.totalCapLabel)
        info_layout.addWidget(self.mapCapLabel)

        main_layout.addLayout(info_layout)
        main_layout.addWidget(scroll, 1)


class MapPoolWidget(QWidget):
    def __init__(
        self,
        pool: MatchmakerQueueMapPool,
        player: Player,
        current_vetoes: dict[str, Counter[str]],
    ) -> None:
        super().__init__()
        self.xd = pool.xd
        self.pool = pool
        self.player = player

        self.total_tokens = pool.tokens
        self.tokens_per_map = pool.max_map_tokens or self.total_tokens + 1
        current_count = current_vetoes.get(self.xd, Counter())
        self.tokens = TokenTracker(self.total_tokens, self.tokens_per_map, current_count)

        self.ui = MapPoolWidgetUI()
        self.ui.setupUi(self)
        self.ui.clearTokensButton.clicked.connect(self.reset_tokens)

        self.map_cards: dict[str, MapCard] = {}
        self._loaded = False

    def on_entered(self) -> None:
        if not self._loaded:
            self.fill_ui()
            self._loaded = True

    def fill_ui(self) -> None:
        self.ui.totalCapLabel.setText(f"Tokens: <b>{self.tokens.remaining}</b>")
        self.ui.mapCapLabel.setText(f"Ban threshold: <b>{self.tokens_per_map}</b>")

        assert self.pool.map_pool is not None
        assert self.pool.map_pool.assignments is not None
        cols = 5
        for idx, assignment in enumerate(self.pool.map_pool.assignments):
            card = MapCard(assignment, self.tokens)
            card.tokens_changed.connect(self.update_appearance)
            card.map_clicked.connect(self.show_map_details)
            card.fill_ui()
            self.map_cards[assignment.xd] = card
            self.ui.mapCardsLayout.addWidget(card, idx // cols, idx % cols)
        self.ui.mapCardsLayout.setRowStretch(self.ui.mapCardsLayout.rowCount(), 1)

    def update_appearance(self) -> None:
        self.ui.totalCapLabel.setText(f"Tokens: <b>{self.tokens.remaining}</b>")

        for card in self.map_cards.values():
            card.update_appearance()

    def reset_tokens(self) -> None:
        self.tokens.reset_tokens()
        for card in self.map_cards.values():
            card.update_appearance()
        self.update_appearance()

    def to_dict(self) -> dict[str, Counter[str]]:
        return {self.xd: self.tokens.counter}

    def show_map_details(self, map_model: HackyMap) -> None:
        widget = MapDetailsWidget(cast(Map, map_model), self.player)
        show_item_details_dialog(widget, self)
        widget.deleteLater()


class MapPoolDialogUI:
    def setupUi(self, widget: QWidget) -> None:
        main_layout = QVBoxLayout(widget)

        self.headerLabel = QLabel("Map Pool Vetoes")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        self.headerLabel.setFont(header_font)
        self.headerLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        button_layout = QHBoxLayout()

        self.clearButton = QPushButton("Clear All Tokens")
        self.confirmButton = QPushButton("Confirm")
        self.cancelButton = QPushButton("Cancel")

        button_layout.addWidget(self.clearButton)
        button_layout.addStretch()
        button_layout.addWidget(self.cancelButton)
        button_layout.addWidget(self.confirmButton)

        main_layout.addWidget(self.headerLabel)
        self.poolTabs = QTabWidget()
        main_layout.addWidget(self.poolTabs)
        main_layout.addLayout(button_layout)


class MapPoolDialog(QDialog):
    def __init__(
        self,
        queue_name: str,
        rating: int,
        player: Player,
        current_vetoes: dict[str, Counter[str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("mapVetoDialog")
        self.queue_name = queue_name
        self.rating = rating
        self.player = player
        self.current_vetoes = current_vetoes

        self.ui = MapPoolDialogUI()
        self.ui.setupUi(self)

        self.ui.headerLabel.setText(f"{queue_name.title()} Map Vetoes")
        self.ui.clearButton.clicked.connect(self.clear_tokens)
        self.ui.confirmButton.clicked.connect(self.accept)
        self.ui.cancelButton.clicked.connect(self.reject)
        self.ui.poolTabs.currentChanged.connect(self.on_pool_tab_changed)

        self.setWindowTitle("Map Pool")
        self.resize(840, 710)

        self.api_connector = MapPoolApiConnector()
        self.api_connector.data_ready.connect(self.on_data)

    def request_pool_info(self) -> None:
        self.api_connector.request_pool_for_queue(self.queue_name)

    def on_data(self, pools: dict[Literal["values"], list[MatchmakerQueueMapPool]]) -> None:
        for index, pool in enumerate(pools["values"]):
            assert pool.map_pool is not None
            pool_widget = MapPoolWidget(pool, self.player, self.current_vetoes)
            self.ui.poolTabs.addTab(pool_widget, self.pool_tab_name(pool))
            if (pool.min_rating or -inf) <= self.rating < (pool.max_rating or inf):
                self.ui.poolTabs.setCurrentIndex(index)

    def pool_tab_name(self, pool: MatchmakerQueueMapPool) -> str:
        if pool.min_rating is None and pool.max_rating is None:
            assert pool.map_pool is not None
            return pool.map_pool.name

        if pool.min_rating is None:
            return f"<{pool.max_rating:.0f}"
        elif pool.max_rating is None:
            return f"{pool.min_rating:.0f}+"
        else:
            return f"{pool.min_rating:.0f}-{pool.max_rating:.0f}"

    def on_pool_tab_changed(self, index: int) -> None:
        pool_widget = cast(MapPoolWidget, self.ui.poolTabs.widget(index))
        pool_widget.on_entered()

    def clear_tokens(self) -> None:
        for index in range(self.ui.poolTabs.count()):
            pool_widget = cast(MapPoolWidget, self.ui.poolTabs.widget(index))
            pool_widget.reset_tokens()

    def applied_vetoes(self) -> dict[str, Counter[str]]:
        ret: dict[str, Counter[str]] = {}
        for index in range(self.ui.poolTabs.count()):
            pool_widget = cast(MapPoolWidget, self.ui.poolTabs.widget(index))
            ret |= pool_widget.to_dict()
        return ret
