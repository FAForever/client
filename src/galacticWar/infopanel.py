#-------------------------------------------------------------------------------
# Copyright (c) 2013 Gael Honorez.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------


from PyQt4 import QtGui
import util
from galacticWar import logger
from attackitem import AttackItem

from teams.teamswidget import TeamWidget

from galacticWar import FACTIONS

FormClass, BaseClass = util.loadUiType("galacticwar/infopanel.ui")

class InfoPanelWidget(FormClass, BaseClass):
    def __init__(self, parent, *args, **kwargs):
        logger.debug("GW Info panel instantiating.")
        BaseClass.__init__(self, *args, **kwargs)
        
        self.setupUi(self)
        self.parent = parent
        self.galaxy = self.parent.galaxy

        self.setup()
        self.attackListWidget.hide()
        
        self.planet = None
        
        
        self.myAttacks      = {}
        self.onlinePlayers    = {}
        
        # if we are waiting for the player list...        
        self.waitingForPlayerList = False
        self.waitingForTeamMemberList = False
        self.teamwidget = TeamWidget(self.parent, {})
        
        
        # Updating stats
        self.parent.creditsUpdated.connect(self.updateCredit)
        self.parent.rankUpdated.connect(self.updateRank)
        self.parent.victoriesUpdated.connect(self.updateVictories)
        self.parent.dominationUpdated.connect(self.updateDomination)
        self.parent.playersListUpdated.connect(self.updatePlayerList)
        self.parent.teamUpdated.connect(self.updateTeam)
        self.parent.searchingUpdated.connect(self.updateSearch)
        
        self.parent.planetClicked.connect(self.planetClicked)
        self.parent.hovering.connect(self.setup)
        self.parent.attacksUpdated.connect(self.updateAttacks)
               
        self.attackButton.clicked.connect(self.attack)
        self.defenseButton.clicked.connect(self.defend)
        self.formTeamButton.clicked.connect(self.formTeam)
        
        self.rankUpButton.clicked.connect(self.rankup)
        self.awayBox.stateChanged.connect(self.away)
        
        self.attackListWidget.itemDoubleClicked.connect(self.giveToattackProposal)

        self.planetaryDefensesButton.clicked.connect(self.buyPlanetaryDefensesItems)
        self.reinforcementButton.clicked.connect(self.buyReinforcementsItems)
        
        self.quitSquadButton.clicked.connect(self.quitSquad)

        self.squadBox.hide()
        self.planetaryDefensesButton.hide()
        self.reinforcementButton.hide()
        self.dominationText.hide()
        self.searchProgress.hide()
        
    def setup(self):
        self.attackButton.hide()
        self.defenseButton.hide()
        
    
    def updateSearch(self, state):
        if state == True:
            self.searchProgress.show()
        else:
            self.searchProgress.hide()
        
    
    def quitSquad(self):
        ''' quit a squad '''
        self.parent.send(dict(command="quit_squad"))
    
    def displaySquad(self):
        ''' display squad infos '''
        
        self.leader.setText("Leader : %s" % self.parent.teams.getLeaderName())
        self.squadMemberList.clear()
        self.squadMemberList.addItems(self.parent.teams.getMemberNames())
        self.squadBox.show()         
        
        if self.parent.teams.getLeaderName() != self.parent.client.login:
            self.formTeamButton.hide()

    
    def updatePlayerList(self, players):
        ''' Triggered when the server sent us the player list '''
        self.onlinePlayers = players
        if self.waitingForPlayerList:
            self.teamwidget.update(players)
            self.teamwidget.show()
            self.waitingForPlayerList = False
        
        if self.waitingForTeamMemberList :
            self.parent.teams.getNames(players)
            self.displaySquad()
            self.waitingForTeamMemberList = False
            
        
            
    def updateTeam(self, message):
        ''' Update teams info'''
        leader = message["leader"]
        members = message["members"]
       
        hasToRequest = False
        self.parent.teams.clearMembers()
        
        if leader == None or members == []:
            self.squadBox.hide()
            self.formTeamButton.show()
            return

        if not leader in self.onlinePlayers.values():
            hasToRequest = True
            self.parent.teams.setLeader(leader, None)
        for uid in members :
            if not uid in self.onlinePlayers.values():
                self.parent.teams.addMember(uid, None)
                hasToRequest = True
        
        self.teamwidget.updateStatus(message)
        
        if hasToRequest:
            self.squadBox.hide()
            self.waitingForTeamMemberList = True
            self.parent.send(dict(command="get_player_list"))
    
        else:
            self.parent.teams.setLeader(leader, self.onlinePlayers.keys()[self.onlinePlayers.values().index(leader)])
            for uid in members:
                self.parent.teams.addMember(uid, self.onlinePlayers.keys()[self.onlinePlayers.values().index(uid)])
            
            self.displaySquad()
    
    def formTeam(self):
        '''Open a request windows to form a team'''
        # asking for player list first.
        self.parent.send(dict(command="get_player_list"))
        self.waitingForPlayerList = True
        
    
    def buyReinforcementsItems(self):
        '''Handle buying reinforcements items'''
        self.parent.send(dict(command="reinforcements_items"))
        self.parent.reinforcementItems.show()   
        
        
    def buyPlanetaryDefensesItems(self):
        '''Handle buying planetary defense items'''
        self.parent.send(dict(command="planetary_defense_items"))
        self.parent.planetaryItems.show()

        
    def giveToattackProposal(self, item):
        ''' give this attack to the second in command system '''
        
        question = QtGui.QMessageBox.question(self, item.itemText, "You are going to give away this attack. Do you want to proceed?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        
        if question == QtGui.QMessageBox.Yes :
            planetuid = item.uid
            self.parent.send(dict(command="send_to_proposal", uid=planetuid))
                
    def updateAttacks(self):
        logger.debug("updating attacks")
        
        membersUids = list(set(self.parent.attacks.keys()).intersection(set(self.parent.teams.getMembersUids() + [self.parent.uid] )))
        myAttackList = [self.parent.attacks[key] for key in membersUids ]

        # first, clear the attacks that are not in the attacklist
        
        for planetuid in set(self.myAttacks.keys()).difference(set([attack.keys()[0] for attack in myAttackList])):
            self.myAttacks[planetuid].updateTimer.stop()
            row = self.attackListWidget.row(self.myAttacks[planetuid])
            if row != None:
                self.attackListWidget.takeItem(row)
            del self.myAttacks[planetuid]        
 
        # then update or add attacks
        for attack in myAttackList : 
            for planetuid in attack:
                if attack[planetuid]["onHold"] == True :
                    if planetuid in self.myAttacks:
                        self.myAttacks[planetuid].updateTimer.stop()
                        row = self.attackListWidget.row(self.myAttacks[planetuid])
                        if row != None:
                            self.attackListWidget.takeItem(row)
                        del self.myAttacks[planetuid]
                    continue
            
            
                if not planetuid in self.myAttacks :
                    self.myAttacks[planetuid] = AttackItem(planetuid)
                    self.attackListWidget.addItem(self.myAttacks[planetuid])            
                
                self.myAttacks[planetuid].update(attack[planetuid], self)

        if self.attackListWidget.count() == 0:
            self.attackListWidget.hide()
        else:
            self.attackListWidget.show()
           

    def away(self, state):
        '''set the player as away'''
        if state == 0 :
            self.parent.send(dict(command="away", state=1))
        else :
            self.parent.send(dict(command="away", state=0))

    def rankup(self):        
        '''handle ranking up '''
        self.parent.send(dict(command="ranking_up"))

    def defend(self):
        '''handle defense'''
        self.parent.send(dict(command="defense_command", uid=self.planet))        
    
    def attack(self):
        self.parent.send(dict(command="attack_command", uid=self.planet))      

    def updateDomination(self, master):
        self.dominationText.setText("You are enslaved by %s and you are fighting for them." % FACTIONS[master])
        self.dominationText.show()

    def updateRank(self, rank):
        logger.debug("updating rank interface")
        rankName = self.parent.get_rank(self.parent.faction, rank)
        self.nameLabel.setText("%s %s" %(rankName,self.parent.name))
        if rank > 0 :
            self.planetaryDefensesButton.show()
            self.reinforcementButton.show()
    
    def updateVictories(self, victories):
        logger.debug("updating victories interface")
        self.victoriesLabel.setText("%i" % victories)
    
    def updateCredit(self, credits):
        logger.debug("updating credit interface")
        self.creditsLabel.setText("%i / %i" % (credits, (1000+ 1000*self.parent.rank)))
    
    def planetClicked(self, planetId):
        ''' When the user click a planet on the map'''

        self.attackButton.hide()
        self.defenseButton.hide()
        
        faction = self.parent.faction

        if self.parent.enslavedBy != None:
            faction = self.parent.enslavedBy

        if faction == None :
            self.planet = None
            return
        
        for uid in self.parent.attacks :
            for planetuid in self.parent.attacks[uid] :
                if planetId == planetuid :
                    if self.parent.attacks[uid][planetuid]["onHold"] == True :
                        if self.parent.attacks[uid][planetuid]["faction"] == faction :
                            self.attackButton.show()
                            self.planet = planetId
                            return
                        return
                    
                    if self.galaxy.control_points[planetuid].occupation(faction) > 0.5 and self.parent.attacks[uid][planetuid]["faction"] != faction :
                        for site in self.galaxy.getLinkedPlanets(planetId) :
                            if self.galaxy.control_points[site].occupation(faction) > 0.5 :
                                self.defenseButton.show()
                                self.planet = planetId
                                return
                    elif self.parent.attacks[uid][planetuid]["faction"] != faction :
                        for site in self.galaxy.getLinkedPlanets(planetId) :
                            if self.galaxy.control_points[site].occupation(faction) > 0.5 :
                                self.attackButton.show()
                                self.planet = planetId
                                return
                    return                        
        
        if self.galaxy.control_points[planetId].occupation(faction) > 0.9 :
            self.planet = None
            return
        
        for site in self.galaxy.getLinkedPlanets(planetId) :
            if self.galaxy.control_points[site].occupation(faction) > 0.5 :
                self.attackButton.show()
                self.planet = planetId
                return


    
