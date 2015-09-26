from functools import partial
import random

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt

import util
from games.gameitem import GameItem, GameItemDelegate
from games.moditem import ModItem, mod_invisible, mods
from games.hostgamewidget import HostgameWidget
from fa.factions import Factions
import fa
import modvault
import notificatation_system as ns

import logging
logger = logging.getLogger(__name__)

FormClass, BaseClass = util.loadUiType("games/games.ui")

class GamesWidget(FormClass, BaseClass):
    def __init__(self, client, *args, **kwargs):

        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)

        self.client = client
        self.client.gamesTab.layout().addWidget(self)

        #Dictionary containing our actual games.
        self.games = {}

        #Ranked search UI
        self.rankedAeon.setIcon(util.icon("games/automatch/aeon.png"))
        self.rankedCybran.setIcon(util.icon("games/automatch/cybran.png"))
        self.rankedSeraphim.setIcon(util.icon("games/automatch/seraphim.png"))
        self.rankedUEF.setIcon(util.icon("games/automatch/uef.png"))
        self.rankedRandom.setIcon(util.icon("games/automatch/random.png"))

        self.join_ladder_listeners = {faction: partial(self.toggle_search, faction) for faction in Factions}

        self.connectRankedToggles()
        self.searchProgress.hide()

        # Ranked search state variables
        self.searching = False
        self.race = None
        self.ispassworded = False
        self.canChooseMap = True

        self.client.modInfo.connect(self.processModInfo)
        self.client.gameInfo.connect(self.processGameInfo)

        self.client.gameEnter.connect(self.stopSearchRanked)
        self.client.viewingReplay.connect(self.stopSearchRanked)

        self.gameList.setItemDelegate(GameItemDelegate(self))
        self.gameList.itemDoubleClicked.connect(self.gameDoubleClicked)
        self.gameList.sortBy = 0 # Default Sorting is By Players count

        self.sortGamesComboBox.addItems(['By Players', 'By Game Quality', 'By avg. Player Rating'])
        self.sortGamesComboBox.currentIndexChanged.connect(self.sortGamesComboChanged)

        self.hideGamesWithPw.stateChanged.connect(self.togglePrivateGames)

        self.modList.itemDoubleClicked.connect(self.hostGameClicked)

        # Load game name from settings (yay, it's persistent!)
        self.load_last_hosted_settings()

    def connectRankedToggles(self):
        self.rankedAeon.toggled.connect(self.join_ladder_listeners[Factions.AEON])
        self.rankedCybran.toggled.connect(self.join_ladder_listeners[Factions.CYBRAN])
        self.rankedSeraphim.toggled.connect(self.join_ladder_listeners[Factions.SERAPHIM])
        self.rankedUEF.toggled.connect(self.join_ladder_listeners[Factions.UEF])
        self.rankedRandom.toggled.connect(self.join_ladder_listeners[Factions.RANDOM])

    def disconnectRankedToggles(self):
        self.rankedAeon.toggled.disconnect(self.join_ladder_listeners[Factions.AEON])
        self.rankedCybran.toggled.disconnect(self.join_ladder_listeners[Factions.CYBRAN])
        self.rankedSeraphim.toggled.disconnect(self.join_ladder_listeners[Factions.SERAPHIM])
        self.rankedUEF.toggled.disconnect(self.join_ladder_listeners[Factions.UEF])
        self.rankedRandom.toggled.disconnect(self.join_ladder_listeners[Factions.RANDOM])

    @QtCore.pyqtSlot(dict)
    def processModInfo(self, message):
        '''
        Slot that interprets and propagates mod_info messages into the mod list
        '''
        item = ModItem(message)

        if message["publish"] :
            self.modList.addItem(item)
        else:
            mod_invisible.append(message["name"])

        if not message["name"] in mods :
            mods[message["name"]] = item

        self.client.replays.modList.addItem(message["name"])

    @QtCore.pyqtSlot(int)
    def togglePrivateGames(self, state):
        # Wow.
        for game in [self.games[game] for game in self.games
                     if self.games[game].state == 'open'
                     and self.games[game].password_protected]:
            game.setHidden(state == Qt.Checked)

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
                self.client.notificationSystem.on_event(ns.NotificationSystem.NEW_GAME, message)
        else:
            self.games[uid].update(message, self.client)

        # Hide private games
        if self.hideGamesWithPw.isChecked() and message['state'] == 'open' and not message['password_protected']:
            self.games[uid].setHidden(True)

        # Special case: removal of a game that has ended
        if message['state'] == "closed":
            if uid in self.games:
                self.gameList.takeItem(self.gameList.row(self.games[uid]))
                del self.games[uid]
            return

    def startSearchRanked(self, race):
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
            self.client.send(dict(command="game_matchmaking", mod="ladder1v1", state="settings", faction = self.race))
        else:
            #Experimental UPnP Mapper - mappings are removed on app exit
            if self.client.useUPnP:
                fa.upnp.createPortMapping(self.client.localIP, self.client.gamePort, "UDP")

            logger.info("Starting Ranked Search as " + str(race) + ", port: " + str(self.client.gamePort))
            self.searching = True
            self.race = race
            self.searchProgress.setVisible(True)
            self.labelAutomatch.setText("Searching...")
            self.client.send(dict(command="game_matchmaking", mod="ladder1v1", state="start", gameport = self.client.gamePort, faction = self.race))

    @QtCore.pyqtSlot()
    def stopSearchRanked(self, *args):
        if (self.searching):
            logger.debug("Stopping Ranked Search")
            self.client.send(dict(command="game_matchmaking", mod="ladder1v1", state="stop"))
            self.searching = False

        self.searchProgress.setVisible(False)
        self.labelAutomatch.setText("1 vs 1 Automatch")

        self.disconnectRankedToggles()
        self.rankedAeon.setChecked(False)
        self.rankedCybran.setChecked(False)
        self.rankedSeraphim.setChecked(False)
        self.rankedUEF.setChecked(False)
        self.connectRankedToggles()

    @QtCore.pyqtSlot(bool)
    def toggle_search(self, faction, enabled):
        if faction == Factions.RANDOM:
            faction = Factions.get_random_faction()

        self.toggleSearch(enabled, faction)

    def toggleSearch(self, state, player_faction):
        """
        Handler called when a ladder search button is pressed. They're really checkboxes, and the
        state flag is used to decide whether to start or stop the search.
        :param state: The checkedness state of the search checkbox that was pushed
        :param player_faction: The faction corresponding to that checkbox
        """
        if (state):
            self.startSearchRanked(player_faction)
            self.disconnectRankedToggles()
            self.rankedAeon.setChecked(False)
            self.rankedCybran.setChecked(False)
            self.rankedUEF.setChecked(False)
            self.rankedRandom.setChecked(False)
            self.connectRankedToggles()
        else:
            self.stopSearchRanked()

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def gameDoubleClicked(self, item):
        '''
        Slot that attempts to join a game.
        '''
        if not fa.instance.available():
            return

        self.stopSearchRanked() #Actually a workaround

        if not fa.check.game(self.client):
            return

        if fa.check.check(item.mod, item.mapname, None, item.mods):
            if item.password_protected:
                passw, ok = QtGui.QInputDialog.getText(self.client, "Passworded game" , "Enter password :", QtGui.QLineEdit.Normal, "")
                if ok:
                    self.client.send(dict(command="game_join", password=passw, uid=item.uid, gameport=self.client.gamePort))
            else :
                self.client.send(dict(command="game_join", uid=item.uid, gameport=self.client.gamePort))

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
        if hostgamewidget.exec_() != 1 :
            return

        # Make sure the binaries are all up to date, and abort if the update fails or is cancelled.
        if not fa.check.game(self.client):
            return

        # Ensure all mods are up-to-date, and abort up if the update process fails.
        if not fa.check.check(item.mod):
            return

        modnames = [str(moditem.text()) for moditem in hostgamewidget.modList.selectedItems()]
        mods = [hostgamewidget.mods[modstr] for modstr in modnames]
        modvault.setActiveMods(mods, True) #should be removed later as it should be managed by the server.

        if self.friends_only:
            visibility = "friends"
        else:
            visibility = "public"

        message = {
            "command": "game_host",
            "visibility": visibility,
            "mod": item.mod,
            "title": self.gamename,
            "mapname": self.gamemap,
            "gameport": self.client.gamePort
        }

        if self.ispassworded:
            message.password = self.gamepassword

        self.client.send(message)

    def load_last_hosted_settings(self):
        util.settings.beginGroup("fa.games")

        # Default of "password"
        self.gamepassword = util.settings.value("password", "password")
        self.gamemap = util.settings.value("gamemap", "scmp_007")
        self.gamename = util.settings.value("gamename", (self.client.login or "") + "'s game")
        self.friends_only = util.settings.value("friends_only", False)

        util.settings.endGroup()

    def save_last_hosted_settings(self, name, map, password = None, friends_only = False):
        self.gamemap = map
        self.gamename = name

        util.settings.beginGroup("fa.games")
        util.settings.setValue("gamemap", map)
        util.settings.setValue("gamename", name)
        util.settings.setValue("friends_only", friends_only)

        if password is not None:
            self.gamePassword = password
            util.settings.setValue("password", password)

        util.settings.endGroup()

    def sortGamesComboChanged(self, index):
        self.gameList.sortBy = index
        self.gameList.sortItems()
