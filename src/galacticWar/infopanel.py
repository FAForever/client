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


from PyQt4 import QtGui, QtCore
import util
from galacticWar import logger
from attackitem import AttackItem
import time

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
        self.attackProposal = {}
        
        # Updating stats
        self.parent.creditsUpdated.connect(self.updateCredit)
        self.parent.rankUpdated.connect(self.updateRank)
        self.parent.victoriesUpdated.connect(self.updateVictories)
        
        
        self.parent.planetClicked.connect(self.planetClicked)
        self.parent.hovering.connect(self.setup)
        self.parent.attacksUpdated.connect(self.updateAttacks)
        
        self.parent.attackProposalUpdated.connect(self.updateAttacksProposal)
        
        self.attackButton.clicked.connect(self.attack)
        self.defenseButton.clicked.connect(self.defend)
        
        self.rankUpButton.clicked.connect(self.rankup)
        self.awayBox.stateChanged.connect(self.away)
        
        self.attackListWidget.itemDoubleClicked.connect(self.giveToattackProposal)
        self.attackProposalListWidget.itemDoubleClicked.connect(self.attackProposalAccepted)

        self.temporaryItemsButton.clicked.connect(self.buyTemporaryItems)

        
    def setup(self):
        self.attackButton.hide()
        self.defenseButton.hide()
        self.attackBox.hide()
        self.temporaryItemsButton.hide()
        
    def buyTemporaryItems(self):
        '''Handle buying temporary items'''
        self.parent.send(dict(command="temporary_items"))
        self.parent.temporaryItems.show()

        
    def giveToattackProposal(self, item):
        ''' give this attack to the second in command system '''
        
        question = QtGui.QMessageBox.question(self, item.itemText, "You are going to give away this attack. Do you want to proceed?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        
        if question == QtGui.QMessageBox.Yes :
            planetuid = item.uid
            self.parent.send(dict(command="send_to_proposal", uid=planetuid))
    
    def attackProposalAccepted(self, item):
        question = QtGui.QMessageBox.question(self, "Second in command", "You are going to attack this planet. Do you want to proceed?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        
        if question == QtGui.QMessageBox.Yes :
            planetuid = item.uid
            self.parent.send(dict(command="accept_proposal", uid=planetuid))
            
    def updateAttacksProposal(self, planetuid):
        if planetuid in self.attackProposal :
            return
        
        self.attackBox.show()
        if not planetuid in self.attackProposal :
            self.attackProposal[planetuid] = AttackItem(planetuid)
            self.attackProposalListWidget.addItem(self.attackProposal[planetuid])
            
            self.attackProposal[planetuid].update(dict(timeAttack=60*10), self)
             
    def updateAttacks(self):
        logger.debug("updating attacks")
        if self.parent.uid in self.parent.attacks :
            
            foundActive = False
            
            for uid in self.parent.attacks[self.parent.uid] :
                if self.parent.attacks[self.parent.uid][uid]["onHold"] == False :
                    foundActive = True
                    break
                
            if foundActive :
                self.attackListWidget.show()
                
                # clearing stuff
                for uid in self.myAttacks :
                    self.myAttacks[uid].updateTimer.stop()
                self.myAttacks = {}
                self.attackListWidget.clear()
                
                for uid in self.parent.attacks[self.parent.uid] :
                    if self.parent.attacks[self.parent.uid][uid]["onHold"] == True :
                        continue
                    
                    if not uid in self.myAttacks :
                        self.myAttacks[uid] = AttackItem(uid)
                        self.attackListWidget.addItem(self.myAttacks[uid])
                    
                    self.myAttacks[uid].update(self.parent.attacks[self.parent.uid][uid], self)
                
        else :
            self.attackListWidget.hide()
            if len(self.myAttacks) != 0 :
                for uid in self.myAttacks :
                    self.myAttacks[uid].updateTimer.stop()
                self.myAttacks = {}
                self.attackListWidget.clear()                

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
    
    def timeOut(self, uid):
        if uid in self.attackProposal :
            item = self.attackProposal[uid]
            item.updateTimer.stop()
            self.attackProposalListWidget.removeItemWidget(item)
            del self.attackProposal[uid]
            
        if len(self.attackProposal) == 0 :
            self.attackBox.hide()           

    def updateRank(self, rank):
        logger.debug("updating rank interface")
        rankName = self.parent.get_rank(self.parent.faction, rank)
        self.nameLabel.setText("%s %s" %(rankName,self.parent.name))
        if rank > 0 :
            self.temporaryItemsButton.show()
    
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
        if faction == None :
            self.planet = None
            return
        
        for uid in self.parent.attacks :
            for planetuid in self.parent.attacks[uid] :
                if planetId == planetuid :
                    if self.parent.attacks[uid][planetuid]["onHold"] == True :
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


    
