from functools import partial
import random

from PyQt5 import QtWidgets
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl, pyqtSlot

import util
from api.featured_mod_api import FeaturedModApiConnector
from config import Settings
from games.moditem import ModItem, mod_invisible
from games.gamemodel import CustomGameFilterModel
from fa.factions import Factions
import fa

import logging

logger = logging.getLogger(__name__)

FormClass, BaseClass = util.THEME.loadUiType("games/games.ui")

class Party:
    def __init__(self, owner_id, members):
        self.owner_id = owner_id
        self.members = [members]
        self.teammates = []
        self.size = len(self.members)

    @property
    def partySize(self):
        return self.size
    
    def setPartySize(self, value):
        self.size = value
    
    def addTeammate(self, teammate):
        self.teammates.append(teammate)
    
    @property
    def getTeammate(self):
        if len(self.teammates) > 0:
            return self.teammates[0]
        else:
            return []

class PartyMember:
    def __init__(self, _id, factions=None):
        self._id = _id
        self.factions = ["uef", "cybran", "aeon", "seraphim"]
        self.login = None

class GamesWidget(FormClass, BaseClass):

    hide_private_games = Settings.persisted_property(
        "play/hidePrivateGames", default_value=False, type=bool)
    sort_games_index = Settings.persisted_property(
        "play/sortGames", default_value=0, type=int)  # Default is by player count
    

    sub_factions_ladder = Settings.persisted_property(
        "play/subFactions", default_value=[False, False, False, False])
    sub_factions_tmm = Settings.persisted_property(
        "play/tmmFactions", default_value=[False, False, False, False])

    def __init__(self, client, game_model, me, gameview_builder, game_launcher):
        BaseClass.__init__(self)
        self.setupUi(self)

        self._me = me
        self.client = client  # type: ClientWindow
        self.mods = {}
        self._game_model = CustomGameFilterModel(self._me, game_model)
        self._game_launcher = game_launcher

        self.apiConnector = FeaturedModApiConnector(self.client.lobby_dispatch)

        self.gameview = gameview_builder(self._game_model, self.gameList)
        self.gameview.game_double_clicked.connect(self.gameDoubleClicked)

        # Ranked search UI
        self._ranked_icons = {
            "ladder1v1": {
                Factions.AEON: self.rankedAeon,
                Factions.CYBRAN: self.rankedCybran,
                Factions.SERAPHIM: self.rankedSeraphim,
                Factions.UEF: self.rankedUEF,
            }, 
            "tmm2v2": {
                Factions.AEON: self.tmmAeon,
                Factions.CYBRAN: self.tmmCybran,
                Factions.SERAPHIM: self.tmmSeraphim,
                Factions.UEF: self.tmmUEF,
            }
        }
        self.rankedAeon.setIcon(util.THEME.icon("games/automatch/aeon.png"))
        self.rankedCybran.setIcon(util.THEME.icon("games/automatch/cybran.png"))
        self.rankedSeraphim.setIcon(util.THEME.icon("games/automatch/seraphim.png"))
        self.rankedUEF.setIcon(util.THEME.icon("games/automatch/uef.png"))

        self.tmmAeon.setIcon(util.THEME.icon("games/automatch/aeon.png"))
        self.tmmCybran.setIcon(util.THEME.icon("games/automatch/cybran.png"))
        self.tmmSeraphim.setIcon(util.THEME.icon("games/automatch/seraphim.png"))
        self.tmmUEF.setIcon(util.THEME.icon("games/automatch/uef.png"))

        # Fixup ini file type loss
        self.sub_factions_ladder = [True if x == 'true' else False for x in self.sub_factions_ladder]
        self.sub_factions_tmm = [True if x == 'true' else False for x in self.sub_factions_tmm]
        self.sub_factions = {"ladder1v1": self.sub_factions_ladder, "tmm2v2": self.sub_factions_tmm}

        self.searchProgress.hide()
        self.tmmProgress.hide()

        # Ranked search state variables
        self.searching = {"ladder1v1": False, "tmm2v2": False}
        self.race = {"ladder1v1": None, "tmm2v2": None}
        self.ispassworded = False

        self.match_found = {"ladder1v1": False, "tmm2v2": False}

        self.party = Party(self._me.id, PartyMember(self._me.id))

        self.generateSelectSubset("ladder1v1")
        self.generateSelectSubset("tmm2v2")

        self.client.lobby_info.modInfo.connect(self.processModInfo)

        self.client.game_enter.connect(self.stopSearch)
        self.client.viewing_replay.connect(self.stopSearch)

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

        self.labelInQueue.setText("-")
        self.hideTmmFrame()
        self.showTMM.clicked.connect(self.setTmmFrame)
        self.kickButton.clicked.connect(self.kick_player_from_party)
        self.leaveButton.clicked.connect(self.leave_party)

        self.updatePlayButton("ladder1v1")
        self.updatePlayButton("tmm2v2")
        self.apiConnector.requestData()

    @pyqtSlot(dict)
    def processModInfo(self, message):
        """
        Slot that interprets and propagates mod_info messages into the mod list
        """
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

    @pyqtSlot(int)
    def togglePrivateGames(self, state):
        self.hide_private_games = state
        self._game_model.hide_private_games = state

    def selectFaction(self, enabled, mod, factionID=0):
        logger.debug('selectFaction: enabled={}, factionID={}'.format(enabled, factionID))
        if len(self.sub_factions[mod]) < factionID:
            logger.warning('selectFaction: len(self.sub_factions) < factionID, aborting')
            return

        logger.debug('selectFaction: selected was {}'.format(self.sub_factions[mod]))
        self.sub_factions[mod][factionID-1] = enabled
        if mod == "ladder1v1":
            Settings.set("play/subFactions", self.sub_factions[mod])
        else:
            Settings.set("play/tmmFactions", self.sub_factions[mod])
        logger.debug('selectFaction: selected is {}'.format(self.sub_factions[mod]))

        if self.party.size > 1:
            factions = self.setFactionSubset(mod)
            self.client.set_faction(factions)
            self.race[mod] = Factions.from_name(factions[random.randint(0, len(factions) - 1)])
        else:
            if self.searching[mod]:
                self.stopSearchRanked(mod)

        self.updatePlayButton(mod)

    def setFactionSubset(self, mod):
        factionSubset = []
        if mod == "ladder1v1":
            if self.rankedUEF.isChecked():
                factionSubset.append("uef")
            if self.rankedCybran.isChecked():
                factionSubset.append("cybran")
            if self.rankedAeon.isChecked():
                factionSubset.append("aeon")
            if self.rankedSeraphim.isChecked():
                factionSubset.append("seraphim")
        else:
            if self.tmmUEF.isChecked():
                factionSubset.append("uef")
            if self.tmmCybran.isChecked():
                factionSubset.append("cybran")
            if self.tmmAeon.isChecked():
                factionSubset.append("aeon")
            if self.tmmSeraphim.isChecked():
                factionSubset.append("seraphim")

        l = len(factionSubset)
        if l == 0:
            factionSubset = ["uef", "cybran", "aeon", "seraphim"]

        return factionSubset

    def startSubRandomRankedSearch(self, mod):
        """
        This is a wrapper around startRankedSearch where a faction will be chosen based on the selected checkboxes
        """
        if self.searching[mod]:
            self.stopSearchRanked(mod)
        else:
            if self.party.size > 1:
                if self.isInGame(self._me.id):
                    QtWidgets.QMessageBox.information(None, "Playing game", "Can't start searching. Your previous game is not over yet.")
                    return
            factions = self.setFactionSubset(mod=mod)
            self.race[mod] = Factions.from_name(factions[random.randint(0, len(factions) - 1)])
            self.startSearchRanked(race=self.race[mod], mod=mod)

    def startViewLadderMapsPool(self):
        QDesktopServices.openUrl(QUrl(Settings.get("MAPPOOL_URL")))

    def generateSelectSubset(self, mod):
        if self.searching[mod]:  # you cannot search for a match while changing/creating the UI
            self.stopSearchRanked(mod)

        if mod == "ladder1v1":
            self.rankedPlay.clicked.connect(partial(self.startSubRandomRankedSearch,mod=mod))
            self.rankedPlay.show()
            self.laddermapspool.clicked.connect(self.startViewLadderMapsPool)
            self.labelRankedHint.show()
        else:
            self.tmmPlay.clicked.connect(partial(self.startSubRandomRankedSearch,mod=mod))
            self.tmmPlay.show()
        
        for faction, icon in list(self._ranked_icons[mod].items()):
            try:
                icon.clicked.disconnect()
            except TypeError:
                pass

            icon.setChecked(self.sub_factions[mod][faction.value-1])
            icon.clicked.connect(partial(self.selectFaction, factionID=faction.value, mod=mod))

    def updatePlayButton(self, mod):
        if self.searching[mod]:
            s = "Stop search"
        else:
            c = self.sub_factions[mod].count(True)
            if c in [0, 4]:  # all or none selected
                s = "Play as random!"
            else:
                s = "Play!"
        if mod == "ladder1v1":
            if self.party.size > 1:
                self.rankedPlay.setEnabled(False)
                self.rankedPlay.setText("Can't search ladder while in party")
            else:
                self.rankedPlay.setEnabled(True)
                self.rankedPlay.setText(s)
        elif mod == "tmm2v2":
            if self.party.size > 1:
                if self.party.owner_id == self._me.id:
                    self.tmmPlay.setText(s)
                    self.tmmPlay.setEnabled(True)
                    self.kickButton.show()
                else:
                    if self.searching[mod]:
                        self.tmmPlay.setText("Party leader will stop searching")
                    else:
                        self.tmmPlay.setText("Party leader will start searching")
                    self.tmmPlay.setEnabled(False)
                    self.kickButton.hide()
                self.partyInfo.show()
            else:
                self.partyInfo.hide()
                self.tmmPlay.setText(s)           

    def startSearchRanked(self, race, mod):
        if fa.instance.running():
            QtWidgets.QMessageBox.information(
                None, "ForgedAllianceForever.exe", "FA is already running.")
            self.stopSearchRanked(mod)
            return

        if not fa.check.check("ladder1v1"):
            self.stopSearchRanked(mod)
            logger.error("Can't play ranked without successfully updating Forged Alliance.")
            return

        if self.searching[mod]:
            logger.info("Switching Ranked Search to Race " + str(race))
            self.client.lobby_connection.send(dict(command="game_matchmaking", mod=mod, state="settings",
                                  faction=self.race[mod].value))
        else:
            logger.info("Starting Ranked Search as " + str(race))
            self.searching[mod] = True
            if mod == "ladder1v1":
                self.searchProgress.setVisible(True)
                self.labelAutomatch.setText("Searching...")

            else:
                self.tmmProgress.setVisible(True)
                self.labelTMM.setText("Searching...")
            
            self.updatePlayButton(mod)
            self.client.search_ranked(faction=self.race[mod].value, mod=mod) 

    def stopSearchRanked(self, mod, *args):
        if self.searching[mod]:
            logger.debug("Stopping Ranked Search")
            self.client.lobby_connection.send(dict(command="game_matchmaking", mod=mod, state="stop"))
            self.searching[mod] = False
            self.match_found[mod] = False

        self.updatePlayButton(mod)
        if mod == "ladder1v1":
            self.searchProgress.setVisible(False)
            self.labelAutomatch.setText("1 vs 1 Automatch")
        else:
            self.tmmProgress.setVisible(False)
            self.labelTMM.setText("2 vs 2 Automatch")

    @pyqtSlot()
    def stopSearch(self, *args):
        self.stopSearchRanked("ladder1v1")
        self.stopSearchRanked("tmm2v2")

    def gameDoubleClicked(self, game):
        """
        Slot that attempts to join a game.
        """
        if not fa.instance.available():
            return

        if self.party.size > 1:
            if not self.leave_party():
                return
        self.stopSearch()  # Actually a workaround

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
       
        if self.party.size > 1:
            if not self.leave_party():
                return
        self.stopSearch()
        self._game_launcher.host_game(item.name, item.mod)

    def sortGamesComboChanged(self, index):
        self.sort_games_index = index
        self._game_model.sort_type = CustomGameFilterModel.SortType(index)

    def updateParty(self, message):
        players_ids = []
        for member in message["members"]:
            players_ids.append(member["player"])

        if self.party.owner_id != message["owner"]:
            self.stopSearch()

        if self.party.size != len(message["members"]):
            self.stopSearch()
        else:
            for member in self.party.members:
                if member._id not in players_ids:
                    self.stopSearch()

        self.party.members.clear()
        self.party.teammates.clear()

        if len(message["members"]) > 1:
            self.party.owner_id = message["owner"]
            self.showTmmFrame()
            for member in message["members"]:
                players_id = member["player"]
                self.party.members.append(PartyMember(_id=players_id, factions=member["factions"]))
                if players_id != self._me.id:
                    self.labelTeammate.setText(str(self.client.players[players_id].login))
                    self.party.teammates.append(PartyMember(_id=players_id, factions=member["factions"]))
        else:
            self.party.owner_id = self._me.id
            self.party.members.append(PartyMember(_id=self._me.id))
            self.labelTeammate.setText('')
        
        self.party.size = len(self.party.members)

        self.updatePlayButton("ladder1v1")
        self.updatePlayButton("tmm2v2")

    
    def showTmmFrame(self):
        self.labelTMM.show()
        self.tmmFrame.show()
        self.showTMM.setText("Hide 2 vs 2 section")
    
    def hideTmmFrame(self):
        self.labelTMM.hide()
        self.tmmFrame.hide()
        self.showTMM.setText("Show 2 vs 2 section")
    
    def setTmmFrame(self):
        if self.tmmFrame.isVisible():
            self.hideTmmFrame()
        else:
            self.showTmmFrame()


    def accept_party_invite(self, sender_id):
        logger.info("Accepting paryt invite from {}".format(sender_id))
        msg = {
            'command': 'accept_party_invite',
            'sender_id': sender_id,
        }
        self.client.lobby_connection.send(msg)

        factions = self.setFactionSubset("tmm2v2")
        self.race["tmm2v2"] = Factions.from_name(factions[random.randint(0, len(factions) - 1)])
        self.client.set_faction(factions)


    def kick_player_from_party(self):
        if self.isInGame(self._me.id):
            QtWidgets.QMessageBox.information(None, "Playing game", "Can't kick. Your party is still in game!")
        else:
            kicked_player_id = self.party.teammates[0]._id
            result = QtWidgets.QMessageBox.question(None, "Kick Player", "Are you sure you want to kick your teammate from party?",
                                                        QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
            if result == QtWidgets.QMessageBox.Yes:
                msg = {
                    'command': 'kick_player_from_party',
                    'kicked_player_id': kicked_player_id,
                }
                self.client.lobby_connection.send(msg)
    
    def leave_party(self):
        result = QtWidgets.QMessageBox.question(None, "Leaving Party", "Are you sure you want to leave party?",
                                                  QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
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
    
    def handle_tmm_search_info(self, message):
        if self.party.size > 1:
            if self.party.owner_id != self._me.id:
                if message["state"] == "start":
                    self.searching["tmm2v2"] = True
                    self.tmmProgress.show()
                    self.updatePlayButton("tmm2v2")
                elif message["state"] == "stop":
                    self.searching["tmm2v2"] = False
                    self.tmmProgress.hide()
                    self.updatePlayButton("tmm2v2")

    def isInGame(self, player_id):
        if self.client.players[player_id].currentGame is None:
            return False
        else:
            return True