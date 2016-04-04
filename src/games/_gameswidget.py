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

import logging

logger = logging.getLogger(__name__)

FormClass, BaseClass = util.loadUiType("games/games.ui")

class GamesWidget(FormClass, BaseClass):

    hide_private_games = Settings.persisted_property("play/hidePrivateGames", default_value=False, type=bool)
    sort_games_index = Settings.persisted_property("play/sortGames", default_value=0, type=int) #Default is by player count

    def __init__(self, client, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)

        self.client = client
        self.client.gamesTab.layout().addWidget(self)

        self.mods = {}

        # Dictionary containing our actual games.
        self.games = {}

        self.canChooseMap = True

        #Ranked search UI
        self._ranked_icons = {
            Factions.AEON: self.rankedAeon,
            Factions.CYBRAN: self.rankedCybran,
            Factions.SERAPHIM: self.rankedSeraphim,
            Factions.UEF: self.rankedUEF,
            Factions.RANDOM: self.rankedRandom
        }
        self.rankedAeon.setIcon(util.icon("games/automatch/aeon.png"))
        self.rankedCybran.setIcon(util.icon("games/automatch/cybran.png"))
        self.rankedSeraphim.setIcon(util.icon("games/automatch/seraphim.png"))
        self.rankedUEF.setIcon(util.icon("games/automatch/uef.png"))
        self.rankedRandom.setIcon(util.icon("games/automatch/random.png"))

        for faction, icon in self._ranked_icons.items():
            icon.clicked.connect(partial(self.toggle_search, faction=faction))

        self.searchProgress.hide()

        # Ranked search state variables
        self.searching = False
        self.race = None
        self.ispassworded = False

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
        # Wow.
        self.hide_private_games = state

        for game in [self.games[game] for game in self.games
                     if self.games[game].state == 'open'
                     and self.games[game].password_protected]:
            game.setHidden(state == Qt.Checked)

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

    def startSearchRanked(self, race):
        for faction, icon in self._ranked_icons.items():
            icon.setChecked(faction == race)

        if race == Factions.RANDOM:
            race = Factions.get_random_faction()

        if fa.instance.running():
            QtGui.QMessageBox.information(None, "ForgedAllianceForever.exe", "FA is already running.")
            self.stopSearchRanked()
            return

        if (not fa.check.check("ladder1v1")):
            self.stopSearchRanked()
            logger.error("Can't play ranked without successfully updating Forged Alliance.")
            return

        if (self.searching):
            logger.info("Switching Ranked Search to Race " + str(race))
            self.race = race
            self.client.send(dict(command="game_matchmaking", mod="ladder1v1", state="settings",
                                  faction=self.race.value))
        else:
            #Experimental UPnP Mapper - mappings are removed on app exit
            if self.client.useUPnP:
                fa.upnp.createPortMapping(self.client.localIP, self.client.gamePort, "UDP")

            logger.info("Starting Ranked Search as " + str(race) + ", port: " + str(self.client.gamePort))
            self.searching = True
            self.race = race
            self.searchProgress.setVisible(True)
            self.labelAutomatch.setText("Searching...")
            self.client.search_ranked(faction=self.race.value)

    @QtCore.pyqtSlot()
    def stopSearchRanked(self, *args):
        if (self.searching):
            logger.debug("Stopping Ranked Search")
            self.client.send(dict(command="game_matchmaking", mod="ladder1v1", state="stop"))
            self.searching = False

        self.searchProgress.setVisible(False)
        self.labelAutomatch.setText("1 vs 1 Automatch")

        for _, icon in self._ranked_icons.items():
            icon.setChecked(False)

    @QtCore.pyqtSlot(bool)
    def toggle_search(self, enabled, faction=None):
        """
        Handler called when a ladder search button is pressed. They're really checkboxes, and the
        state flag is used to decide whether to start or stop the search.
        :param state: The checkedness state of the search checkbox that was pushed
        :param player_faction: The faction corresponding to that checkbox
        """
        if enabled:
            self.startSearchRanked(faction)
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
                passw, ok = QtGui.QInputDialog.getText(self.client, "Passworded game" , "Enter password :", QtGui.QLineEdit.Normal, "")
                if ok:
                    self.client.join_game(uid=item.uid, password=passw)
            else:
                self.client.join_game(uid=item.uid)

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def hostGameClicked(self, item):
        '''
        Hosting a game event
        '''
        self.load_last_hosted_settings()
        if not fa.instance.available():
            return

        self.stopSearchRanked()

        hostgamewidget = HostgameWidget(self, item)
        # Abort if the client cancelled the host game dialogue.
        if hostgamewidget.exec_() != 1:
            return

        # Make sure the binaries are all up to date, and abort if the update fails or is cancelled.
        if not fa.check.game(self.client):
            return

        # Ensure all mods are up-to-date, and abort if the update process fails.
        if not fa.check.check(item.mod):
            return

        modnames = [str(moditem.text()) for moditem in hostgamewidget.modList.selectedItems()]
        mods = [hostgamewidget.mods[modstr] for modstr in modnames]
        modvault.setActiveMods(mods, True)

        self.client.host_game(title=self.gamename,
                              mod=item.mod,
                              visibility="friends" if self.friends_only else "public",
                              mapname=self.gamemap,
                              password=self.gamepassword if self.ispassworded else None)

    def load_last_hosted_settings(self):
        util.settings.beginGroup("fa.games")

        # Default of "password"
        self.gamepassword = util.settings.value("password", "password")
        self.gamemap = util.settings.value("gamemap", "scmp_007")
        if self.client.login:
            self.gamename = util.settings.value("gamename", "{}'s game".format(self.client.login))
        else:
            self.gamename = util.settings.value("gamename", "Nobody's game")

        self.friends_only = util.settings.value("friends_only", False, type=bool)

        util.settings.endGroup()

    def save_last_hosted_settings(self, name, map, password = None, friends_only = False):
        self.gamemap = map
        self.gamename = name

        util.settings.beginGroup("fa.games")
        util.settings.setValue("gamemap", map)
        if name != "Nobody's game":
            util.settings.setValue("gamename", name)
        util.settings.setValue("friends_only", friends_only)

        if password is not None:
            self.gamepassword = password
            self.ispassworded = True
            util.settings.setValue("password", password)
        else:
            self.ispassworded = False

        util.settings.endGroup()

    def sortGamesComboChanged(self, index):
        self.sort_games_index = index;
        self.gameList.sortBy = index
        self.gameList.sortItems()
