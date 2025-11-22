from __future__ import annotations

import logging
from copy import deepcopy
from functools import partial
from typing import TYPE_CHECKING

from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets

from src import fa
from src import util
from src.api.matchmaker_queue_api import MatchmakerQueueApiConnector
from src.config import Settings
from src.fa.factions import Factions
from src.games.mappoolwidget import MapPoolDialog

FormClass, BaseClass = util.THEME.loadUiType("games/automatchframe.ui")

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow
    from src.games._gameswidget import GamesWidget


class MatchmakerQueue(FormClass, BaseClass):

    def __init__(
            self,
            games: GamesWidget,
            client: ClientWindow,
            queueName: str,
            teamSize: int,
    ) -> None:
        BaseClass.__init__(self, games)
        self.setupUi(self)

        self.queueName = queueName
        self.teamSize = teamSize
        self.subFactions = Settings.get(
            f"play/{self.queueName}Factions",
            default=[False] * 4,
            type=bool,
        )
        self.games = games
        self.client = client
        self.client.matchmaker_info.connect(self.handleQueueInfo)
        self.games.matchmaker_search_info.connect(self.handleSearchInfo)
        self.games.match_found_message.connect(self.handleMatchFound)
        self.games.stop_search_ranked_game.connect(self.stopSearchRanked)
        self.games.party_updated.connect(self.handlePartyUpdate)

        self._rankedIcons = {
            Factions.AEON: self.rankedAeon,
            Factions.CYBRAN: self.rankedCybran,
            Factions.SERAPHIM: self.rankedSeraphim,
            Factions.UEF: self.rankedUEF,
        }
        self.rankedUEF.setIcon(util.THEME.icon("games/automatch/uef.png"))
        self.rankedAeon.setIcon(util.THEME.icon("games/automatch/aeon.png"))
        self.rankedCybran.setIcon(
            util.THEME.icon("games/automatch/cybran.png"),
        )
        self.rankedSeraphim.setIcon(
            util.THEME.icon("games/automatch/seraphim.png"),
        )

        self.searching = False
        self.updatePlayButton()

        self.rankedPlay.clicked.connect(self.startSearchRanked)
        self.rankedPlay.show()
        self.mapsPool.clicked.connect(self.view_map_pool)

        self.setFactionIcons(self.subFactions)

        key_combination = QtCore.QKeyCombination(
            QtCore.Qt.KeyboardModifier.ControlModifier,
            (
                QtCore.Qt.Key.Key_1,
                QtCore.Qt.Key.Key_2,
                QtCore.Qt.Key.Key_3,
                QtCore.Qt.Key.Key_4,
            )[self.teamSize - 1],
        )
        self.shortcut = QtGui.QShortcut(
            QtGui.QKeySequence(key_combination),
            self.client,
            self.startSearchRanked,
        )

        self.matchmakerTimer = QtCore.QTimer()
        self.matchmakerTimer.timeout.connect(self.updateMatchmakerTimer)
        self.secondsToAutomatch = 0

        self.ratingType = ""
        self.apiConnector = MatchmakerQueueApiConnector()
        self.apiConnector.data_ready.connect(self.handleApiQueueInfo)
        self.apiConnector.requestData({"include": "leaderboard"})

        title = self.queueName.replace("_", " ").capitalize()
        self.automatchTitle.setText(title)

    def setFactionIcons(self, subFactions):
        for faction, icon in self._rankedIcons.items():
            try:
                icon.clicked.disconnect()
            except TypeError:
                pass
            icon.setChecked(subFactions[faction.value - 1])
            icon.clicked.connect(
                partial(self.selectFaction, factionID=faction.value),
            )

    def handleApiQueueInfo(self, message):
        for queue in message.get("values", {}):
            if queue["technicalName"] == self.queueName:
                self.ratingType = queue["ratingType"]

    def handleQueueInfo(self, message):
        for queue in message.get("queues", {}):
            if queue["queue_name"] == self.queueName:
                self.labelInQueue.setText(
                    "In Queue: {}".format(queue["num_players"]),
                )
                self.secondsToAutomatch = int(queue["queue_pop_time_delta"])
                self.updateLabelMatchingIn()
                self.matchmakerTimer.start(1 * 1000)

    def handleSearchInfo(self, message):
        if message["queue_name"] == self.queueName:
            self.searching = message["state"] == "start"
            self.games.searching[self.queueName] = self.searching
            self.updatePlayButton()

    def handleMatchFound(self, message):
        if message.get("queue_name", "") == self.queueName:
            # clear but do not cancel search
            self.searching = False
            self.games.searching[self.queueName] = False
            self.updatePlayButton()

    def updateMatchmakerTimer(self):
        if self.secondsToAutomatch > 0:
            self.secondsToAutomatch -= 1
            self.updateLabelMatchingIn()

    def updateLabelMatchingIn(self):
        minutes, seconds = divmod(self.secondsToAutomatch, 60)
        self.labelMatchingIn.setText(f"Matching In: {int(minutes):02}:{int(seconds):02}")

    def startSearchRanked(self):
        if (
            self.games.party.member_count > self.teamSize
            or self.games.party.owner_id != self.client.me.id
        ):
            return

        if self.searching:
            self.stopSearchRanked()
            return

        if not any(self.games.searching.values()):
            if fa.instance.running():
                QtWidgets.QMessageBox.information(
                    self.client,
                    "ForgedAllianceForever.exe",
                    "FA is already running.",
                )
                self.stopSearchRanked()
                return

            if not fa.check.check("ladder1v1"):
                self.stopSearchRanked()
                logger.error(
                    "Can't play ranked without successfully "
                    "updating Forged Alliance.",
                )
                return

        logger.debug("Starting Ranked Search. Queue: %s", self.queueName)
        self.client.search_ranked(queue_name=self.queueName)

    def stopSearchRanked(self):
        if self.searching:
            logger.debug("Stopping Ranked Search")
            self.client.lobby_connection.send(
                dict(
                    command="game_matchmaking",
                    queue_name=self.queueName,
                    state="stop",
                ),
            )
            self.searching = False
            self.games.searching[self.queueName] = False
            self.updatePlayButton()

    def handlePartyUpdate(self):
        if (
            self.games.party.member_count > self.teamSize
            or self.games.party.owner_id != self.client.me.id
        ):
            self.rankedPlay.setEnabled(False)
        else:
            self.rankedPlay.setEnabled(True)

    def updatePlayButton(self):
        index = self.games.matchmakerQueues.indexOf(self)
        if self.searching:
            s = "Stop search"
            self.searchProgress.show()
            self.games.matchmakerQueues.tabBar().setTabTextColor(
                index, QtGui.QColor("orange"),
            )
        else:
            c = self.subFactions.count(True)
            if c in [0, 4]:
                s = "Play as random!"
            else:
                s = "Play!"
            self.searchProgress.hide()
            self.games.matchmakerQueues.tabBar().setTabTextColor(
                index, QtGui.QColor("silver"),
            )
        self.rankedPlay.setText(s)

    def view_map_pool(self) -> None:
        if self.client.me.player is None:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(Settings.get("MAPPOOL_URL")))
        else:
            rating = self.client.me.player.rating_estimate(self.ratingType)
            dialog = MapPoolDialog(
                self.queueName,
                rating,
                self.client.me.player,
                deepcopy(self.games.vetoes),
                self.client,
            )
            dialog.request_pool_info()
            if dialog.exec() == dialog.DialogCode.Accepted:
                vetoes = dialog.applied_vetoes()
                self.games.update_matchmaker_vetoes(vetoes)
            dialog.deleteLater()

    def selectFaction(self, enabled, factionID=0):
        if len(self.subFactions) < factionID:
            return
        self.subFactions[factionID - 1] = enabled
        Settings.set(f"play/{self.queueName}Factions", self.subFactions)
        self.updatePlayButton()
