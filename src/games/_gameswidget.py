import logging

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QCursor

import fa
import util
from api.featured_mod_api import FeaturedModApiConnector
from config import Settings
from games.automatchframe import MatchmakerQueue
from games.gamemodel import CustomGameFilterModel
from games.moditem import ModItem, mod_invisible
from model.chat.channel import PARTY_CHANNEL_SUFFIX

logger = logging.getLogger(__name__)

FormClass, BaseClass = util.THEME.loadUiType("games/games.ui")


class Party:
    def __init__(self, owner_id=-1, owner=None):
        self.owner_id = owner_id
        self.members = [owner] if owner else []

    @property
    def memberCount(self):
        return len(self.memberList)

    @property
    def memberList(self):
        return self.members

    def addMember(self, member):
        self.memberList.append(member)

    @property
    def memberIds(self):
        uids = []
        if len(self.members) > 0:
            for member in self.members:
                uids.append(member.id_)
        return uids

    def __eq__(self, other):
        if (
            sorted(self.memberIds) == sorted(other.memberIds) and
            self.owner_id == other.owner_id
        ):
            return True
        else:
            return False


class PartyMember:
    def __init__(self, id_=-1, factions=None):
        self.id_ = id_
        self.factions = ["uef", "cybran", "aeon", "seraphim"]


class GamesWidget(FormClass, BaseClass):

    hide_private_games = Settings.persisted_property(
        "play/hidePrivateGames", default_value=False, type=bool)
    sort_games_index = Settings.persisted_property(
        "play/sortGames", default_value=0, type=int)  # Default is by player count

    matchmaker_search_info = pyqtSignal(dict)
    match_found_message = pyqtSignal(dict)
    stop_search_ranked_game = pyqtSignal()
    party_updated = pyqtSignal()

    def __init__(self, client, game_model, me, gameview_builder, game_launcher):
        BaseClass.__init__(self, client)
        self.setupUi(self)

        self._me = me
        self.client = client  # type: ClientWindow
        self.mods = {}
        self._game_model = CustomGameFilterModel(self._me, game_model)
        self._game_launcher = game_launcher

        self.apiConnector = FeaturedModApiConnector(self.client.lobby_dispatch)

        self.gameview = gameview_builder(self._game_model, self.gameList)
        self.gameview.game_double_clicked.connect(self.gameDoubleClicked)

        self.matchFoundQueueName = ""
        self.ispassworded = False
        self.party = None

        self.client.lobby_info.modInfo.connect(self.processModInfo)

        self.client.matchmaker_info.connect(self.handleMatchmakerInfo)
        self.client.game_enter.connect(self.stopSearch)
        self.client.viewing_replay.connect(self.stopSearch)
        self.client.authorized.connect(self.onAuthorized)

        self.sortGamesComboBox.addItems(['By Players', 'By avg. Player Rating', 'By Map', 'By Host', 'By Age'])
        self.sortGamesComboBox.currentIndexChanged.connect(self.sortGamesComboChanged)
        try:
            CustomGameFilterModel.SortType(self.sort_games_index)
            safe_sort_index = self.sort_games_index
        except ValueError:
            safe_sort_index = 0
        # This only triggers the signal if the index actually changes,
        # so let's initialize it ourselves
        self.sortGamesComboBox.setCurrentIndex(safe_sort_index)
        self.sortGamesComboChanged(safe_sort_index)

        self.hideGamesWithPw.stateChanged.connect(self.togglePrivateGames)
        self.hideGamesWithPw.setChecked(self.hide_private_games)

        self.modList.itemDoubleClicked.connect(self.hostGameClicked)
        self.teamList.itemPressed.connect(self.teamListItemClicked)

        self.hidePartyInfo()
        self.leaveButton.clicked.connect(self.leave_party)

        self.apiConnector.requestData()

        self.searching = {"ladder1v1": False}
        self.matchmakerShortcuts = []

        self.matchmakerFramesInitialized = False

    def refreshMods(self):
        self.apiConnector.requestData()

    def onAuthorized(self, me):
        if not self.mods:
            self.refreshMods()
        if self.party is None:
            self.party = Party(me.id, PartyMember(me.id))
        if not self.matchmakerFramesInitialized:
            self.client.lobby_connection.send(dict(command="matchmaker_info"))

    def onLogOut(self):
        self.stopSearch()
        self.party = None
        while self.matchmakerQueues.widget(0) is not None:
            self.matchmakerQueues.widget(0).deleteLater()
            self.matchmakerQueues.removeTab(0)
        for shortcut in self.matchmakerShortcuts:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self.matchmakerShortcuts.clear()
        self.matchmakerFramesInitialized = False

    @pyqtSlot(dict)
    def processModInfo(self, message):
        """
        Slot that interprets and propagates mod_info messages into the mod list
        """
        for value in message["values"]:
            mod = value['name']
            old_mod = self.mods.get(mod, None)
            self.mods[mod] = ModItem(value)

            if old_mod:
                if mod in mod_invisible:
                    del mod_invisible[mod]
                for i in range(0, self.modList.count()):
                    if self.modList.item(i) == old_mod:
                        self.modList.takeItem(i)
                for i in range(self.client.replays.modList.count()):
                    if self.client.replays.modList.itemText(i) == old_mod.mod:
                        self.client.replays.modList.removeItem(i)

            if value["publish"]:
                self.modList.addItem(self.mods[mod])
            else:
                mod_invisible[mod] = self.mods[mod]

            self.client.replays.modList.addItem(value["name"])

    @pyqtSlot(int)
    def togglePrivateGames(self, state):
        self.hide_private_games = state
        self._game_model.hide_private_games = state

    def stopSearch(self):
        self.searching = {"ladder1v1": False}
        self.labelAutomatchInfo.setText("")
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
                self.party is not None and
                self.party.memberCount > 1 and not self.leave_party()
        ):
            return
        self.stopSearch()

        if not fa.check.game(self.client):
            return

        if fa.check.check(game.featured_mod, mapname=game.mapname, version=None, sim_mods=game.sim_mods):
            if game.password_protected:
                passw, ok = QtWidgets.QInputDialog.getText(
                    self.client, "Passworded game", "Enter password :", QtWidgets.QLineEdit.Normal, "")
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
                self.party is not None and
                self.party.memberCount > 1 and not self.leave_party()
        ):
            return
        self.stopSearch()
        self._game_launcher.host_game(item.name, item.mod)

    def sortGamesComboChanged(self, index):
        self.sort_games_index = index
        self._game_model.sort_type = CustomGameFilterModel.SortType(index)

    def teamListItemClicked(self, item):
        if QtWidgets.QApplication.mouseButtons() == Qt.LeftButton:
            # for no good reason doesn't always work as expected
            item.setSelected(False)

        if (
            QtWidgets.QApplication.mouseButtons() == Qt.RightButton and
            self.party.owner_id == self._me.id
        ):
            self.teamList.setCurrentItem(item)
            playerLogin = item.data(0)
            playerId = self.client.players[playerLogin].id
            menu = QtWidgets.QMenu(self)
            actionKick = QtWidgets.QAction("Kick from party", menu)
            actionKick.triggered.connect(
                lambda: self.kickPlayerFromParty(playerId)
            )
            menu.addAction(actionKick)
            menu.popup(QCursor.pos())

    def updateParty(self, message):
        players_ids = []
        for member in message["members"]:
            players_ids.append(member["player"])

        old_owner = self.client.players[self.party.owner_id]
        new_owner = self.client.players[message["owner"]]
        if (
            old_owner.id != new_owner.id or
            self._me.id not in players_ids or
            len(message["members"]) < 2
        ):
            self.client._chatMVC.connection.part(
                "#{}{}".format(old_owner.login, PARTY_CHANNEL_SUFFIX)
            )

        new_party = Party()
        if len(message["members"]) > 1 and self._me.id in players_ids:
            new_party.owner_id = new_owner.id
            for member in message["members"]:
                players_id = member["player"]
                new_party.addMember(
                    PartyMember(id_=players_id, factions=member["factions"])
                )
        else:
            new_party.owner_id = self._me.id
            new_party.addMember(PartyMember(id_=self._me.id))

        if self.party != new_party:
            self.stopSearch()
            self.party = new_party
            if self.party.memberCount > 1:
                self.client._chatMVC.connection.join(
                    "#{}{}".format(new_owner.login, PARTY_CHANNEL_SUFFIX)
                )
            self.updateTeamList()

        self.updatePartyInfoFrame()
        self.party_updated.emit()

    def showPartyInfo(self):
        self.partyInfo.show()

    def hidePartyInfo(self):
        self.partyInfo.hide()

    def updatePartyInfoFrame(self):
        if self.party.memberCount > 1:
            self.showPartyInfo()
        else:
            self.hidePartyInfo()

    def updateTeamList(self):
        self.teamList.clear()
        for member_id in self.party.memberIds:
            if member_id != self._me.id:
                item = QtWidgets.QListWidgetItem(
                    self.client.players[member_id].login
                )
                if member_id == self.party.owner_id:
                    item.setIcon(util.THEME.icon("chat/rank/partyleader.png"))
                else:
                    item.setIcon(util.THEME.icon("chat/rank/newplayer.png"))
                self.teamList.addItem(item)

    def accept_party_invite(self, sender_id):
        self.stopSearch()
        logger.info("Accepting paryt invite from {}".format(sender_id))
        msg = {
            'command': 'accept_party_invite',
            'sender_id': sender_id,
        }
        self.client.lobby_connection.send(msg)

    def kickPlayerFromParty(self, playerId):
        login = self.client.players[playerId].login
        result = QtWidgets.QMessageBox.question(
            self, "Kick Player: {}".format(login),
            "Are you sure you want to kick {} from party?".format(login),
            QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
        )
        if result == QtWidgets.QMessageBox.Yes:
            self.stopSearch()
            msg = {
                'command': 'kick_player_from_party',
                'kicked_player_id': playerId,
            }
            self.client.lobby_connection.send(msg)

    def leave_party(self):
        result = QtWidgets.QMessageBox.question(
            self, "Leaving Party", "Are you sure you want to leave party?",
            QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
        )
        if result == QtWidgets.QMessageBox.Yes:
            msg = {
                'command': 'leave_party'
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
        self.labelAutomatchInfo.setText("Match found! Waiting for launch...")
        self.match_found_message.emit(message)

    def handleMatchCancelled(self, message):
        # the match cancelled message from the server can appear way too late,
        # so any notifications or actions may be confusing if the user found a
        # match but then aborted it and found a new one or joined/hosted a
        # custom game
        ...

    def isInGame(self, player_id):
        if self.client.players[player_id].currentGame is None:
            return False
        else:
            return True

    def handleMatchmakerInfo(self, message):
        # there were cases when ladder info came earlier than the answer
        # to client's matchmaker_info request, so probably it will need to be
        # fully hardcoded when everything comes out, but for now just
        # need to be sure that there are at least 2 queues in message
        if (
            not self.matchmakerFramesInitialized and
            len(message.get("queues", {})) > 1
        ):
            logger.info("Initializing matchmaker queue frames")
            queues = message.get("queues", {})
            queues.sort(key=lambda queue: queue["team_size"])
            for index, queue in enumerate(queues):
                self.matchmakerQueues.insertTab(
                    index,
                    MatchmakerQueue(
                        self, self.client,
                        queue["queue_name"], queue["team_size"]
                    ),
                    "&{teamSize} vs {teamSize}".format(
                        teamSize=queue["team_size"]
                    )
                )
            for index in range(self.matchmakerQueues.tabBar().count()):
                self.matchmakerQueues.tabBar().setTabTextColor(
                    index, QColor("silver")
                )
            self.matchmakerFramesInitialized = True
