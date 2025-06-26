from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Self

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QCursor

from src import fa
from src import util
from src.api.featured_mod_api import FeaturedModApiConnector
from src.client.user import User
from src.games.automatchframe import MatchmakerQueue
from src.games.filters.controller import GamesSortFilterController
from src.games.filters.sortfiltermodel import CustomGameFilterModel
from src.games.gameitem import GameViewBuilder
from src.games.gamemodel import GameModel
from src.games.hostgamewidget import GameLauncher
from src.games.moditem import ModItem
from src.games.moditem import mod_invisible
from src.model.chat.channel import PARTY_CHANNEL_SUFFIX
from src.protocol.lobbyprotocol import ServerMessage

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow

logger = logging.getLogger(__name__)


FormClass, BaseClass = util.THEME.loadUiType("games/games.ui")


class Party:
    def __init__(self, owner_id: int = -1, owner: PartyMember | None = None) -> None:
        self.owner_id = owner_id
        self.members = [owner] if owner else []

    @property
    def member_count(self) -> int:
        return len(self.members)

    def add_member(self, member: PartyMember) -> None:
        self.members.append(member)

    @property
    def member_ids(self) -> list[int]:
        return [member.id_ for member in self.members]

    def __eq__(self, other: Self) -> bool:
        return set(self.member_ids) == set(other.member_ids) and self.owner_id == other.owner_id


class PartyMember:
    def __init__(self, id_: int = -1, factions: list[str] | None = None) -> None:
        self.id_ = id_
        self.factions = factions


class GamesWidget(FormClass, BaseClass):
    matchmaker_search_info = pyqtSignal(dict)
    match_found_message = pyqtSignal(dict)
    stop_search_ranked_game = pyqtSignal()
    party_updated = pyqtSignal()

    def __init__(
            self,
            client: ClientWindow,
            game_model: GameModel,
            me: User,
            gameview_builder: GameViewBuilder,
            game_launcher: GameLauncher,
    ) -> None:
        BaseClass.__init__(self, client)
        self.setupUi(self)

        self._me = me
        self.client = client  # type - ClientWindow
        self.mods = {}
        self._game_filter_model = CustomGameFilterModel(self.client.user_relations, game_model)
        self._game_filter_controller = GamesSortFilterController(
            self._game_filter_model,
            self.gamesShownCountLabel,
            self.applyFilters,
            self.hideGamesWithPw,
            self.hideGamesWithMods,
            self.manageGameFiltersButton,
            self.sortGamesComboBox,
        )
        self._game_launcher = game_launcher

        self.apiConnector = FeaturedModApiConnector()
        self.apiConnector.data_ready.connect(self.process_mod_info)

        self.gameview = gameview_builder(self._game_filter_model, self.gameList)
        self.gameview.game_double_clicked.connect(self.gameDoubleClicked)

        self.matchFoundQueueName = ""
        self.ispassworded = False
        self.party = None

        self.client.matchmaker_info.connect(self.handle_matchmaker_info)
        self.client.game_enter.connect(self.stopSearch)
        self.client.viewing_replay.connect(self.stopSearch)
        self.client.authorized.connect(self.on_authorized)

        self.modList.itemDoubleClicked.connect(self.hostGameClicked)
        self.teamList.itemPressed.connect(self.teamListItemClicked)

        self.hidePartyInfo()
        self.leaveButton.clicked.connect(self.leave_party)

        self.apiConnector.requestData()

        self.searching = {"ladder1v1": False}
        self.matchmakerShortcuts = []

    def refreshMods(self):
        self.apiConnector.requestData()

    def on_authorized(self, me: User) -> None:
        if not self.mods:
            self.refreshMods()
        if self.party is None:
            self.party = Party(me.id, PartyMember(me.id))
        self.client.lobby_connection.send({"command": "matchmaker_info"})

    def on_logout(self) -> None:
        self.stopSearch()
        self.party = None
        while self.matchmakerQueues.widget(0) is not None:
            self.matchmakerQueues.widget(0).deleteLater()
            self.matchmakerQueues.removeTab(0)
        for shortcut in self.matchmakerShortcuts:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self.matchmakerShortcuts.clear()

    @pyqtSlot(dict)
    def process_mod_info(self, message: dict) -> None:
        """
        Slot that interprets and propagates mod_info messages into the mod list
        """
        for featured_mod in message["values"]:
            mod = featured_mod.name
            old_mod = self.mods.get(mod, None)
            self.mods[mod] = ModItem(featured_mod)

            if old_mod:
                if mod in mod_invisible:
                    del mod_invisible[mod]
                for i in range(0, self.modList.count()):
                    if self.modList.item(i) == old_mod:
                        self.modList.takeItem(i)
                for i in range(self.client.replays.modList.count()):
                    if self.client.replays.modList.itemText(i) == old_mod.mod:
                        self.client.replays.modList.removeItem(i)

            if featured_mod.visible:
                self.modList.addItem(self.mods[mod])
            else:
                mod_invisible[mod] = self.mods[mod]

            self.client.replays.modList.addItem(mod)

    def stopSearch(self):
        self.searching = {"ladder1v1": False}
        self.client.labelAutomatchInfo.setText("")
        self.client.labelAutomatchInfo.hide()
        if self.matchFoundQueueName:
            self.matchFoundQueueName = ""
        self.stop_search_ranked_game.emit()

    def gameDoubleClicked(self, game):
        """
        Slot that attempts to join a game.
        """
        if not fa.instance.available():
            return

        if (
            self.party is not None
            and self.party.member_count > 1
            and not self.leave_party()
        ):
            return
        self.stopSearch()

        if not fa.check.game(self.client):
            return

        if fa.check.check(
            game.featured_mod, mapname=game.mapname,
            version=None, sim_mods=game.sim_mods,
        ):
            if game.password_protected:
                passw, ok = QtWidgets.QInputDialog.getText(
                    self.client,
                    "Passworded game",
                    "Enter password :",
                    QtWidgets.QLineEdit.EchoMode.Normal,
                    "",
                )
                if ok:
                    self.client.join_game(uid=game.uid, password=passw)
            else:
                self.client.join_game(uid=game.uid)

    @pyqtSlot(QtWidgets.QListWidgetItem)
    def hostGameClicked(self, item):
        """
        Hosting a game event
        """
        if not fa.instance.available():
            return

        if (
            self.party is not None
            and self.party.member_count > 1
            and not self.leave_party()
        ):
            return
        self.stopSearch()
        self._game_launcher.host_game(item.name, item.mod)

    def teamListItemClicked(self, item):
        if QtWidgets.QApplication.mouseButtons() == Qt.MouseButton.LeftButton:
            # for no good reason doesn't always work as expected
            item.setSelected(False)

        if (
            QtWidgets.QApplication.mouseButtons() == Qt.MouseButton.RightButton
            and self.party.owner_id == self._me.id
        ):
            self.teamList.setCurrentItem(item)
            playerLogin = item.data(0)
            playerId = self.client.players[playerLogin].id
            menu = QtWidgets.QMenu(self)
            actionKick = QAction("Kick from party", menu)
            actionKick.triggered.connect(
                lambda: self.kickPlayerFromParty(playerId),
            )
            menu.addAction(actionKick)
            menu.popup(QCursor.pos())

    def updateParty(self, message):
        players_ids = [member["player"] for member in message["members"]]

        old_owner = self.client.players[self.party.owner_id]
        new_owner = self.client.players[message["owner"]]
        if (
            old_owner.id != new_owner.id
            or self._me.id not in players_ids
            or len(message["members"]) < 2
        ):
            self.client._chatMVC.connection.part(
                f"#{old_owner.login}{PARTY_CHANNEL_SUFFIX}",
            )

        new_party = Party()
        if len(message["members"]) > 1 and self._me.id in players_ids:
            new_party.owner_id = new_owner.id
            for member in message["members"]:
                players_id = member["player"]
                new_party.add_member(PartyMember(id_=players_id, factions=member["factions"]))
        else:
            new_party.owner_id = self._me.id
            new_party.add_member(PartyMember(id_=self._me.id))

        if self.party != new_party:
            self.stopSearch()
            self.party = new_party
            if self.party.member_count > 1:
                self.client._chatMVC.connection.join(
                    f"#{new_owner.login}{PARTY_CHANNEL_SUFFIX}",
                )
            self.updateTeamList()

        self.updatePartyInfoFrame()
        self.party_updated.emit()

    def showPartyInfo(self):
        self.partyInfo.show()

    def hidePartyInfo(self):
        self.partyInfo.hide()

    def updatePartyInfoFrame(self) -> None:
        if self.party.member_count > 1:
            self.showPartyInfo()
        else:
            self.hidePartyInfo()

    def updateTeamList(self) -> None:
        self.teamList.clear()
        for member_id in self.party.member_ids:
            if member_id != self._me.id:
                item = QtWidgets.QListWidgetItem(
                    self.client.players[member_id].login,
                )
                if member_id == self.party.owner_id:
                    item.setIcon(util.THEME.icon("chat/rank/partyleader.png"))
                else:
                    item.setIcon(util.THEME.icon("chat/rank/newplayer.png"))
                self.teamList.addItem(item)

    def accept_party_invite(self, sender_id):
        self.stopSearch()
        logger.info("Accepting party invite from %d", sender_id)
        msg = {
            'command': 'accept_party_invite',
            'sender_id': sender_id,
        }
        self.client.lobby_connection.send(msg)

    def kickPlayerFromParty(self, playerId):
        login = self.client.players[playerId].login
        result = QtWidgets.QMessageBox.question(
            self, f"Kick Player: {login}",
            f"Are you sure you want to kick {login} from party?",
            QtWidgets.QMessageBox.StandardButton.Yes, QtWidgets.QMessageBox.StandardButton.No,
        )
        if result == QtWidgets.QMessageBox.StandardButton.Yes:
            self.stopSearch()
            msg = {
                'command': 'kick_player_from_party',
                'kicked_player_id': playerId,
            }
            self.client.lobby_connection.send(msg)

    def leave_party(self):
        result = QtWidgets.QMessageBox.question(
            self, "Leaving Party", "Are you sure you want to leave party?",
            QtWidgets.QMessageBox.StandardButton.Yes, QtWidgets.QMessageBox.StandardButton.No,
        )
        if result == QtWidgets.QMessageBox.StandardButton.Yes:
            msg = {
                'command': 'leave_party',
            }
            self.client.lobby_connection.send(msg)

            if self.isInGame(self._me.id):
                self.client.players[self._me.id]._currentGame = None
            return True
        else:
            return False

    def handleMatchmakerSearchInfo(self, message):
        self.matchmaker_search_info.emit(message)

    def handleMatchFound(self, message):
        self.matchFoundQueueName = message.get("queue_name", "")
        self.match_found_message.emit(message)

    def isInGame(self, player_id):
        if self.client.players[player_id].currentGame is None:
            return False
        else:
            return True

    def handle_matchmaker_info(self, message: ServerMessage) -> None:
        for queue in message.get("queues", {}):
            insert_to = queue["team_size"] - 1
            existing_queue = self.matchmakerQueues.widget(insert_to)
            if existing_queue is None or existing_queue.teamSize != queue["team_size"]:
                logger.info("Adding matchmaker queue %s", queue["queue_name"])
                mqueue = MatchmakerQueue(self, self.client, queue["queue_name"], queue["team_size"])
                mqueue.handleQueueInfo(message)
                tab_name = "&{teamSize} vs {teamSize}".format(teamSize=queue["team_size"])
                self.matchmakerQueues.insertTab(insert_to, mqueue, tab_name)
                self.matchmakerQueues.tabBar().setTabTextColor(insert_to, QColor("silver"))
