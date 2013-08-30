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
from galacticWar import logger
import util
from reinforcementItem import ReinforcementItem, ReinforcementDelegate

FormClass, BaseClass = util.loadUiType("galacticwar/reinforcementItems.ui")


class groupsReinforcements(object):
    def __init__(self, parent):
        self.parent = parent
        self.reinforcements = self.parent.reinforcements
        self.groups = {}
        self.protectedGroups = []
    
    def addGroupItem(self, group, uid, amount, protected=False):
        ''' add an item to a group'''
        if not group in self.groups:
            self.groups[group] = []
        
        if not self.itemExistsInGroup(group, uid):
            self.groups[group].append(groupItem(self, uid, amount))
            if protected :
                if not group in self.protectedGroups:
                    self.protectedGroups.append(group)
   
    def itemExistsInGroup(self, group, uid):
        if group in self.groups:
            for item in self.getItems(group):
                if item.uid == uid:
                    return True
        return False
   
    def getGroups(self):
        ''' get group numbers'''
        return self.groups.keys()
    
    def getGroupPrice(self, group):
        ''' return the price of a group'''
        groupPrice = 0
        if group in self.groups:
            for item in self.getItems(group):
                groupPrice = groupPrice + (item.price * item.amount)
        return groupPrice

    def getNextGroupNumber(self):
        if len(self.getGroups()) == 0:
            return 0 
        return max(self.getGroups()) + 1
    
    def getItems(self, group):
        ''' return the items in a group '''
        if group in self.groups:
            return self.groups[group]
        return []

    def remove(self, group):
        if group in self.groups:
            if not self.isProtected(group):
                del self.groups[group]
            
    def emptyAll(self):
        ''' delete everything because it's obselete'''
        self.groups = {}
        self.protectedGroups = []        

    def isProtected(self, group):
        ''' check if a group is read only'''
        if group in self.protectedGroups:
            return True
        return False    

class groupItem(object):
    def __init__(self, parent, uid, amount, protected=False):
        ''' init the group with the correct data'''
        self.parent = parent
        self.uid=uid
        self.amount=amount
        self.name =self.parent.reinforcements[uid].name
        self.price = self.parent.reinforcements[uid].price
        self.delay = self.parent.reinforcements[uid].delay
        
    def getItemForSend(self):
        '''return a dictionnary compatible with the server format'''
        return dict(unit=self.uid, amount=self.amount)
        

class ReinforcementWidget(FormClass, BaseClass):
    def __init__(self, parent, *args, **kwargs):
        logger.debug("GW Temporary item instantiating.")
        BaseClass.__init__(self, *args, **kwargs)
        
        self.setupUi(self)
        self.parent = parent

        self.reinforcementListWidget.setItemDelegate(ReinforcementDelegate(self))
        
        self.parent.ReinforcementUpdated.connect(self.processReinforcementInfo)
        self.parent.ReinforcementsGroupUpdated.connect(self.processReinforcementGroup)
        self.parent.playersListUpdated.connect(self.updatePlayerList)
        self.parent.creditsUpdated.connect(self.updateCreditsCheck)
        
        
        self.reinforcementListWidget.itemPressed.connect(self.itemPressed)

        self.reinforcements = {}
        
        
        self.confirmGroupButton.clicked.connect(self.confirmGroup)
        self.buyButton.clicked.connect(self.buyAll)
        self.offerButton.clicked.connect(self.offer)
        self.groups = groupsReinforcements(self)
        
        self.groupsWidgets.itemPressed.connect(self.myGroupsPressed)
        
        self.currentMoneyCost = 0
        self.currentGroupMoneyCost = 0

        self.waitingForPlayerList = False
        
        self.groupDelayText.setText("0")
        self.GroupCostText.setText("0")
        self.CostText.setText("0 minutes")

    def updatePlayerList(self, players):
        ''' update the player list for offering units'''
        if self.waitingForPlayerList:
            player, ok = QtGui.QInputDialog.getItem(self, "Select a player",
                "Give to:", sorted(players.keys()), 0, False)
        if ok and player:
            for group in self.groups.getGroups():
                if self.groups.isProtected(group):
                    continue
                    
                for item in self.groups.getItems(group):
                    self.parent.send(dict(command="offer_reinforcement_group", giveTo=players[player], item=item.getItemForSend()))

                    
            self.groups.emptyAll()
            self.groupsWidgets.clear()
            self.currentMoneyCost = 0
            self.currentGroupMoneyCost = 0
            self.groupDelayText.setText("0")
            self.GroupCostText.setText("0")
            self.CostText.setText("0 minutes")            
            
        self.waitingForPlayerList = False

    def reset(self):
        ''' close the panel and reset all units'''
        self.groups.emptyAll()
        self.groupsWidgets.clear()
        self.groupsOwned.clear()
        self.currentMoneyCost = 0
        self.currentGroupMoneyCost = 0

        self.groupDelayText.setText("0")
        self.GroupCostText.setText("0")
        self.CostText.setText("0 minutes")
        self.close()

    def offer(self):
        ''' send a message to the server about our nice offer'''

        self.parent.send(dict(command="get_player_list"))
        self.waitingForPlayerList = True

    def buyAll(self):
        ''' send a message to the server about our shopping list'''

        for group in self.groups.getGroups():
            if self.groups.isProtected(group):
                continue

            for item in self.groups.getItems(group):
                self.parent.send(dict(command="buy_reinforcement_group", groupNumber=group, item=item.getItemForSend()))
            
        self.groups.emptyAll()
        self.groupsWidgets.clear()
        self.currentMoneyCost = 0
        self.currentGroupMoneyCost = 0
        self.groupDelayText.setText("0")
        self.GroupCostText.setText("0")
        self.CostText.setText("0 minutes")
        
    def myGroupsPressed(self, item):
        '''Options for existing groups'''
        
        if QtGui.QApplication.mouseButtons() != QtCore.Qt.RightButton:
            return
        
        menu = QtGui.QMenu(self.groupsWidgets)
        
        # Actions
        actionDelete = QtGui.QAction("Delete group", menu)
        menu.addAction(actionDelete)
        
        # Triggers
        actionDelete.triggered.connect(lambda : self.deleteGroup(item.group))
 
        # Adding to menu
        menu.addAction(actionDelete)

        #Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())        
        
    def deleteGroup(self, group):
        '''Delete a group'''

        if self.groups.isProtected(group):
            return
        
        groupPrice = self.groups.getGroupPrice(group)
                
        self.currentMoneyCost = self.currentMoneyCost - groupPrice
        self.groups.remove(group)
        
        
        # update the interface
        self.computeAllCosts() 
        self.updateGroupTree()
        self.updateCreditsCheck()


    def confirmGroup(self):
        '''add this group'''

        group = self.groups.getNextGroupNumber()
         
        for uid in self.reinforcements:
            if self.reinforcements[uid].owned != 0:
                self.groups.addGroupItem(group, uid, self.reinforcements[uid].owned)
           
        if len(self.groups.getGroups()) == 0:
            return
         
       
        self.currentMoneyCost = self.currentMoneyCost + self.currentGroupMoneyCost

        #clear the current group buy
        for uid in self.reinforcements:
            self.reinforcements[uid].owned = 0
        
        self.computeAllCosts()
        self.updateCreditsCheck()
        
        self.updateGroupTree(temp=True)
        
    def updateGroupTree(self, temp=False):
        '''Update the group tree'''
        if temp:
            self.groupsWidgets.clear()
        else:
            self.groupsOwned.clear()
#        if len(self.groups.getGroups()) == 0:
#            return

        totaldelay = 0
        for groupNumber in self.groups.getGroups():
            if self.groups.isProtected(groupNumber) and temp:
                continue
            group_item = QtGui.QTreeWidgetItem()
            
            price = 0
            delay = 0
            for item in self.groups.getItems(groupNumber):
                formation_item = QtGui.QTreeWidgetItem()
                formation_item.group = groupNumber
                totPrice = item.price * item.amount
                formation_item.setText(0,"%s x%i (%i credits)" % (item.name, item.amount, totPrice))

                price = price + totPrice 
                delay = delay + item.delay * item.amount
            
                group_item.addChild(formation_item)

            totaldelay = totaldelay + delay 
            group_item.setText(0, "Group %i : %i credits, %0.1f minutes delay (%0.1f minutes in game)" % (groupNumber, price, delay, totaldelay))
            group_item.group = groupNumber
            if temp:
                self.groupsWidgets.addTopLevelItem(group_item)
            else:
                self.groupsOwned.addTopLevelItem(group_item)
            group_item.setExpanded(True)

                
    def itemPressed(self, item):
        '''buy or unbuy an item'''
        if QtGui.QApplication.mouseButtons() == QtCore.Qt.LeftButton:
            if not item.disabled:
                item.add()
        else:
            item.remove()
        
        self.computeAllCosts()
        self.updateCreditsCheck()

    def updateCreditsCheck(self):
        '''disable item we can't buy'''
        for uid in self.reinforcements:
            if not self.reinforcements[uid].isHidden():
                if self.parent.credits - (self.currentMoneyCost + self.currentGroupMoneyCost) < self.reinforcements[uid].price:
                    self.reinforcements[uid].setDisabled()
                else:
                    self.reinforcements[uid].setEnabled()
                    
    def computeAllCosts(self):
        ''' compute the costs'''
        self.currentGroupMoneyCost = 0
        delay = 0.0
        for uid in self.reinforcements:
            if self.reinforcements[uid].owned != 0:
                self.currentGroupMoneyCost = self.currentGroupMoneyCost + (self.reinforcements[uid].price * self.reinforcements[uid].owned)  
                delay = delay + (self.reinforcements[uid].delay * self.reinforcements[uid].owned)
        
        currentMoneyCost =  self.currentMoneyCost + self.currentGroupMoneyCost  
        
        self.CostText.setText("%i" % currentMoneyCost)
        self.GroupCostText.setText("%i" % self.currentGroupMoneyCost)
        self.groupDelayText.setText("%0.1f minutes" % delay)
    
    def processReinforcementGroup(self, message):
        '''Handle a reinforcementGroup info message'''
        
        group = message["group"]
        uid = message["unit"]
        amount = message["amount"]
        
        self.groups.addGroupItem(group, uid, amount, True)
        
        self.updateGroupTree()
        
        
    
    def processReinforcementInfo(self, message):
        '''Handle a reinforcement info message'''
        uid = message["uid"]
        if uid not in self.reinforcements:
            self.reinforcements[uid] = ReinforcementItem(uid)
            self.reinforcementListWidget.addItem(self.reinforcements[uid])
            self.reinforcements[uid].update(message, self.parent)
        else:
            self.reinforcements[uid].update(message, self.parent)
        
        self.updateCreditsCheck()