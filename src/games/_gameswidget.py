from functools import partial
import random

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt

import util
from config import Settings
from games.gameitem import GameItem, GameItemDelegate
from games.moditem import ModItem, mod_invisible, mods
from games.hostgamewidget import HostgameWidget
from fa.factions import Factions
import fa
import modvault
import notifications as ns
from config import Settings

import logging

logger = logging.getLogger(__name__)

FormClass, BaseClass = util.loadUiType("games/games.ui")


class GamesWidget(FormClass, BaseClass):

    hide_private_games = Settings.persisted_property(
        "play/hidePrivateGames", default_value=False, type=bool)
    sort_games_index = Settings.persisted_property(
        "play/sortGames", default_value=0, type=int)  # Default is by player count
    sub_factions = Settings.persisted_property(
        "play/subFactions", default_value=['false', 'false', 'false', 'false'])

    def __init__(self, client, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)

        self.client = client
        self.client.gamesTab.layout().addWidget(self)

        self.mods = {}

        # Dictionary containing our actual games.
        self.games = {}

        # Ranked search UI
        self._ranked_icons = {
            Factions.AEON: self.rankedAeon,
            Factions.CYBRAN: self.rankedCybran,
            Factions.SERAPHIM: self.rankedSeraphim,
            Factions.UEF: self.rankedUEF,
        }
        self.rankedAeon.setIcon(util.icon("games/automatch/aeon.png"))
        self.rankedCybran.setIcon(util.icon("games/automatch/cybran.png"))
        self.rankedSeraphim.setIcon(util.icon("games/automatch/seraphim.png"))
        self.rankedUEF.setIcon(util.icon("games/automatch/uef.png"))

        self.searchProgress.hide()

        # Ranked search state variables
        self.searching = False
        self.race = None
        self.ispassworded = False

        self.generateSelectSubset()

        self.client.modInfo.connect(self.processModInfo)
        self.client.gameInfo.connect(self.processGameInfo)
        self.client.disconnected.connect(self.clear_games)

        self.client.gameEnter.connect(self.stopSearchRanked)
        self.client.viewingReplay.connect(self.stopSearchRanked)

        self.gameList.setItemDelegate(GameItemDelegate(self))
        self.gameList.itemDoubleClicked.connect(self.gameDoubleClicked)
        self.gameList.sortBy = self.sort_games_index  # Default Sorting is By Players count

        self.sortGamesComboBox.addItems(['By Players', 'By Game Quality', 'By avg. Player Rating'])
        self.sortGamesComboBox.currentIndexChanged.connect(self.sortGamesComboChanged)
        self.sortGamesComboBox.setCurrentIndex(self.sort_games_index)

        self.hideGamesWithPw.stateChanged.connect(self.togglePrivateGames)
        self.hideGamesWithPw.setChecked(self.hide_private_games)

        self.modList.itemDoubleClicked.connect(self.hostGameClicked)


    @QtCore.pyqtSlot(dict)
    def processModInfo(self, message):
        '''
        Slot that interprets and propagates mod_info messages into the mod list
        '''
        mod = message['name']
        old_mod = self.mods.get(mod, None)
        self.mods[mod] = ModItem(message)

        if old_mod:
            if mod in mod_invisible:
                del mod_invisible[mod]
            for i in range(0, self.modList.count()):
                if self.modList.item(i) == old_mod:
                    self.modList.takeItem(i)
                    continue

        if message["publish"]:
            self.modList.addItem(self.mods[mod])
        else:
            mod_invisible[mod] = self.mods[mod]

        self.client.replays.modList.addItem(message["name"])

    @QtCore.pyqtSlot(int)
    def togglePrivateGames(self, state):
        self.hide_private_games = state

        for game in [self.games[game] for game in self.games if self.games[game].state == 'open' and self.games[game].password_protected]:
            game.setHidden(state == Qt.Checked)

    def selectFaction(self, enabled, factionID=0):
        if len(self.sub_factions) <= factionID:
            return

        self.sub_factions[factionID] = 'true' if enabled else 'false'

        Settings.set("play/subFactions", self.sub_factions)

        if self.searching:
            self.stopSearchRanked()

    def startSubRandomRankedSearch(self):
        '''
        This is a wrapper around startRankedSearch where a faction will be chosen based on the selected checkboxes
        '''
        if self.searching:
            self.stopSearchRanked()
        else:
            factionSubset = []

            if self.rankedUEF.isChecked():
                factionSubset.append("uef")
            if self.rankedCybran.isChecked():
                factionSubset.append("cybran")
            if self.rankedAeon.isChecked():
                factionSubset.append("aeon")
            if self.rankedSeraphim.isChecked():
                factionSubset.append("seraphim")

            l = len(factionSubset)
            if l in [0, 4]:
                self.startSearchRanked(Factions.RANDOM)
            else:
                # chooses a random factionstring from factionsubset and converts it to a Faction
                self.startSearchRanked(Factions.from_name(
                    factionSubset[random.randint(0, l - 1)]))

    def generateSelectSubset(self):
        if self.searching:  # you cannot search for a match while changing/creating the UI
            self.stopSearchRanked()

        self.rankedPlay.clicked.connect(self.startSubRandomRankedSearch)
        self.rankedPlay.show()
        self.labelRankedHint.hide()
        self.labelSubsetRankedHint.show()
        for faction, icon in self._ranked_icons.items():
            try:
                icon.clicked.disconnect()
            except TypeError:
                pass

            icon.setChecked(self.sub_factions[faction.value] == 'true')
            icon.clicked.connect(partial(self.selectFaction, factionID=faction.value))

    @QtCore.pyqtSlot()
    def clear_games(self):
        self.games = {}
        self.gameList.clear()

    @QtCore.pyqtSlot(dict)
    def processGameInfo(self, message):
        '''
        Slot that interprets and propagates game_info messages into GameItems
        '''
        uid = message["uid"]

        if uid not in self.games:
            self.games[uid] = GameItem(uid)
            self.gameList.addItem(self.games[uid])
            self.games[uid].update(message, self.client)

            if message['state'] == 'open' and not message['password_protected']:
                self.client.notificationSystem.on_event(ns.Notifications.NEW_GAME, message)
        else:
            self.games[uid].update(message, self.client)

        # Hide private games
        if self.hideGamesWithPw.isChecked() and message['state'] == 'open' and message['password_protected']:
            self.games[uid].setHidden(True)

        # Special case: removal of a game that has ended
        if message['state'] == "closed":
            if uid in self.games:
                self.gameList.takeItem(self.gameList.row(self.games[uid]))
                del self.games[uid]

    def updatePlayButton(self):
        if self.searching:
            s = "Stop search"
        else:
            s = "Play!"

        self.rankedPlay.setText(s)

    def startSearchRanked(self, race):
        if race == Factions.RANDOM:
            race = Factions.get_random_faction()

        if fa.instance.running():
            QtGui.QMessageBox.information(
                None, "ForgedAllianceForever.exe", "FA is already running.")
            self.stopSearchRanked()
            return

        if not fa.check.check("ladder1v1"):
            self.stopSearchRanked()
            logger.error("Can't play ranked without successfully updating Forged Alliance.")
            return

        if self.searching:
            logger.info("Switching Ranked Search to Race " + str(race))
            self.race = race
            self.client.send(dict(command="game_matchmaking", mod="ladder1v1", state="settings",
                                  faction=self.race.value))
        else:
            # Experimental UPnP Mapper - mappings are removed on app exit
            if self.client.useUPnP:
                fa.upnp.createPortMapping(self.client.localIP, self.client.gamePort, "UDP")

            logger.info("Starting Ranked Search as " + str(race) +
                        ", port: " + str(self.client.gamePort))
            self.searching = True
            self.race = race
            self.searchProgress.setVisible(True)
            self.labelAutomatch.setText("Searching...")
            self.updatePlayButton();
            self.client.search_ranked(faction=self.race.value)

    @QtCore.pyqtSlot()
    def stopSearchRanked(self, *args):
        if self.searching:
            logger.debug("Stopping Ranked Search")
            self.client.send(dict(command="game_matchmaking", mod="ladder1v1", state="stop"))
            self.searching = False

        self.updatePlayButton()
        self.searchProgress.setVisible(False)
        self.labelAutomatch.setText("1 vs 1 Automatch")


    @QtCore.pyqtSlot(bool)
    def toggle_search(self, enabled, race=None):
        """
        Handler called when a ladder search button is pressed. They're really checkboxes, and the
        state flag is used to decide whether to start or stop the search.
        :param state: The checkedness state of the search checkbox that was pushed
        :param player_faction: The faction corresponding to that checkbox
        """
        if enabled and not self.searching:
            self.startSearchRanked(race)
        else:
            self.stopSearchRanked()

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def gameDoubleClicked(self, item):
        '''
        Slot that attempts to join a game.
        '''
        if not fa.instance.available():
            return

        self.stopSearchRanked()  # Actually a workaround

        if not fa.check.game(self.client):
            return

        if fa.check.check(item.mod, mapname=item.mapname, version=None, sim_mods=item.mods):
            if item.password_protected:
                passw, ok = QtGui.QInputDialog.getText(
                    self.client, "Passworded game", "Enter password :", QtGui.QLineEdit.Normal, "")
                if ok:
                    self.client.join_game(uid=item.uid, password=passw)
            else:
                self.client.join_game(uid=item.uid)

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def hostGameClicked(self, item):
        '''
        Hosting a game event
        '''
        if not fa.instance.available():
            return

        self.stopSearchRanked()

        hostgamewidget = HostgameWidget(self, item)
        # Abort if the client cancelled the host game dialogue.
        if hostgamewidget.exec_() != 1:
            return

    def sortGamesComboChanged(self, index):
        self.sort_games_index = index
        self.gameList.sortBy = index
        self.gameList.sortItems()
