from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QCursor
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QFormLayout
from PyQt6.QtWidgets import QFrame
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtWidgets import QListWidget
from PyQt6.QtWidgets import QListWidgetItem
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.api.models.Player import ClanMembership
from src.util import utctolocal

if TYPE_CHECKING:
    from src.contextmenu.playercontextmenu import PlayerContextMenu


class ClanMembershipTabUi:
    def setupUi(self, widget: QWidget) -> None:
        main_layout = QVBoxLayout(widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.clanOverview = self.create_clan_overview()
        main_layout.addWidget(self.clanOverview)
        self.membersSection = self.create_members_section()
        main_layout.addWidget(self.membersSection)

        self.noClan = QLabel("<h1>Player is not a member of any clan</h1>")
        self.noClan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.noClan)

    def create_clan_overview(self) -> QGroupBox:
        group_box = QGroupBox()
        layout = QVBoxLayout()
        header_layout = QHBoxLayout()

        self.clanName = QLabel()
        self.clanName.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header_layout.addWidget(self.clanName)

        header_layout.addStretch()

        self.websiteButton = QPushButton("Visit Website")
        header_layout.addWidget(self.websiteButton)

        layout.addLayout(header_layout)
        layout.addSpacing(20)

        self.detailsLayout = QHBoxLayout()

        desc_layout = QVBoxLayout()
        desc_label = QLabel("Description:")
        desc_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        desc_layout.addWidget(desc_label)

        self.clanDescription = QTextEdit()
        self.clanDescription.setReadOnly(True)
        desc_layout.addWidget(self.clanDescription)
        self.detailsLayout.addLayout(desc_layout)
        layout.addLayout(self.detailsLayout)

        group_box.setLayout(layout)
        group_box.setMaximumHeight(240)
        return group_box

    def create_members_section(self) -> QGroupBox:
        group_box = QGroupBox()

        layout = QVBoxLayout()

        search_layout = QHBoxLayout()
        search_label = QLabel("Search members:")
        search_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))

        self.clearSearchButton = QPushButton("Clear")

        search_layout.addWidget(search_label)

        self.searchInput = QLineEdit()
        self.searchInput.setPlaceholderText("Enter player name to search...")
        search_layout.addWidget(self.searchInput)
        search_layout.addWidget(self.clearSearchButton)

        layout.addLayout(search_layout)
        layout.addSpacing(10)

        self.membersList = QListWidget()
        self.membersList.setObjectName("clanMembersList")
        self.membersList.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.membersList.setSpacing(6)
        self.membersList.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)

        layout.addWidget(self.membersList)
        group_box.setLayout(layout)
        return group_box


class ClanMembershipTab(QWidget):
    def __init__(self, menu: PlayerContextMenu, membership: ClanMembership | None = None) -> None:
        super().__init__()
        self.menu = menu
        self.membership_data = membership

        self.ui = ClanMembershipTabUi()
        self.ui.setupUi(self)
        if self.membership_data is not None:
            self.init_ui()

    def init_ui(self) -> None:
        if self.membership_data is not None:
            self.ui.noClan.hide()

            clan = self.membership_data.custom_clan
            assert clan is not None

            self.ui.searchInput.textChanged.connect(self.filter_members)
            self.ui.websiteButton.pressed.connect(
                lambda: QDesktopServices.openUrl(QUrl(clan.website_url)),
            )
            self.ui.clearSearchButton.clicked.connect(self.clear_search)

            self.ui.membersList.itemPressed.connect(self.on_clan_member_selected)

            self.ui.clanName.setText(f"{clan.name} [{clan.tag}]")
            self.ui.clanDescription.setPlainText(clan.description)
            details = (
                (
                    ("Clan ID:", clan.xd),
                    ("Created:", utctolocal(clan.create_time)),
                    ("Members:", str(len(clan.memberships or []))),
                ),
                (
                    ("Invitation Required:", "Yes" if clan.requires_invitation else "No"),
                    ("Leader:", clan.leader.login if clan.leader is not None else "-"),
                    ("Founder:", clan.founder.login if clan.founder is not None else "-"),
                ),
            )
            for index, form in enumerate(details):
                form_layout = QFormLayout()
                for label, value in form:
                    label_widget = QLabel(label)
                    label_widget.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                    form_layout.addRow(label_widget, QLabel(value))
                self.ui.detailsLayout.insertLayout(index, form_layout)
            if (memberships := clan.memberships) is not None:
                self.populate_members_list(memberships)
        else:
            self.ui.clanOverview.hide()
            self.ui.membersSection.hide()

    def create_member_card(self, member_data: ClanMembership) -> QFrame:
        frame = QFrame()
        frame.setObjectName("clanMember")
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QHBoxLayout()

        player_info = QVBoxLayout()

        assert member_data.player is not None
        name_label = QLabel(member_data.player.login)
        name_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        player_info.addWidget(name_label)

        details_text = f"<small>Joined: {utctolocal(member_data.create_time)}</small>"
        details_label = QLabel(details_text)
        player_info.addWidget(details_label)

        layout.addLayout(player_info)
        layout.addStretch()

        details_layout = QFormLayout()
        details_layout.addRow(
            QLabel("<small>Account created:</small>"),
            QLabel(f"<small>{utctolocal(member_data.player.create_time)}</small>"),
        )
        details_layout.addRow(
            QLabel("<small>Last seen:</small"),
            QLabel(f"<small>{utctolocal(member_data.player.update_time)}</small>"),
        )
        layout.addLayout(details_layout)

        frame.setLayout(layout)
        return frame

    def populate_members_list(self, memberships: list[ClanMembership]) -> None:
        self.ui.membersList.clear()

        for membership in memberships:
            item = QListWidgetItem()

            member_widget = self.create_member_card(membership)

            item.setSizeHint(member_widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, membership)

            self.ui.membersList.addItem(item)
            self.ui.membersList.setItemWidget(item, member_widget)

    def filter_members(self, text: str) -> None:
        search_text = text.lower().strip()

        for i in range(self.ui.membersList.count()):
            item = self.ui.membersList.item(i)
            assert item is not None
            member_data = item.data(Qt.ItemDataRole.UserRole)

            if member_data and member_data.player is not None:
                player_name = member_data.player.login.lower()
                item.setHidden(search_text != "" and search_text not in player_name)

    def clear_search(self) -> None:
        self.ui.searchInput.clear()
        for i in range(self.ui.membersList.count()):
            item = self.ui.membersList.item(i)
            assert item is not None
            item.setHidden(False)

    def set_membership(self, membership: ClanMembership | None) -> None:
        self.membership_data = membership
        self.init_ui()

    def on_clan_member_selected(self, item: QListWidgetItem) -> None:
        if QApplication.mouseButtons() != Qt.MouseButton.RightButton:
            return
        player = item.data(Qt.ItemDataRole.UserRole).player
        menu = self.menu.get_context_menu(player.login, int(player.xd))
        menu.popup(QCursor.pos())
