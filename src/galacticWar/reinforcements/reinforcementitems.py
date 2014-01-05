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
from reinforcementItem import ReinforcementItem, ReinforcementDelegate, ReinforcementGroupDelegate
import cPickle
import pickle

FormClass, BaseClass = util.loadUiType("galacticwar/reinforcementItems.ui")


class groupListWidget(QtGui.QListWidget):
    def __init__(self, parent, group, *args, **kwargs):
        QtGui.QListWidget.__init__(self, *args, **kwargs)
        self.parent = parent
        self.group = group
        self.setMouseTracking(1)
        self.setAutoFillBackground(False)
        self.setAcceptDrops(True)
        
        self.setItemDelegate(ReinforcementGroupDelegate(self.parent))
        self.groupUnits = {}

        self.mouseMoveEvent = self.mouseMove
          
    def deleteAll(self):
        self.clear()
        self.groupUnits = {}      

    def startDrag(self, event):
        ''' Draging owned units'''
        index = self.indexAt(event.pos())
        if not index.isValid():
            return

        ## selected is the relevant person object
        selected = dict(group = self.group, uid = self.model().data(index, QtCore.Qt.UserRole).uid)
        bstream = cPickle.dumps(selected)
        mimeData = QtCore.QMimeData()
        mimeData.setData("application/x-ownedunit-reinforcement", bstream)

        drag = QtGui.QDrag(self)
        drag.setMimeData(mimeData)
        
        drag.setPixmap(self.itemAt(event.pos()).icon().pixmap(50,50))
        
        drag.setHotSpot(QtCore.QPoint(0,0))
        drag.start(QtCore.Qt.MoveAction) 

    def mouseMove(self, event):
        ''' moving items'''
        self.startDrag(event)
          
    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-ownedunit-reinforcement"):
            data = event.mimeData()
            bstream = data.retrieveData("application/x-ownedunit-reinforcement", QtCore.QVariant.ByteArray)

            message = pickle.loads(bstream)
            uid         = message["uid"]
            groupFrom   = message["group"]
            
            otherGroup = self.parent.unitsGroup[groupFrom]
            
            if uid in otherGroup.groupUnits:
                infos = otherGroup.groupUnits[uid].getInfos()
                if infos["owned"] == 0:
                    event.ignore()
                    return

                elif infos["owned"] != 1:
                    i, ok = QtGui.QInputDialog.getInteger(self,
                "Amount", "How many units do you want in this group?", infos["owned"], 1, infos["owned"], 1)
                    if ok:
                        infos["owned"] = i
                
                otherGroup.groupUnits[uid].remove(infos["owned"])
                
                if uid not in self.groupUnits:
                    self.groupUnits[uid] = ReinforcementItem(uid, small=True)
                    self.addItem(self.groupUnits[uid])
                    self.groupUnits[uid].update(infos, self.parent.parent)
                else:
                    self.groupUnits[uid].add(infos["owned"])            
            
            
            self.parent.parent.send(dict(command="move_reinforcement_group", origin = groupFrom, destination = self.group, itemuid=uid, amount=infos["owned"]))
            
            event.accept()
            return
        
        event.ignore()
        
    def dragEnterEvent(self, event) :
        if event.mimeData().hasFormat("application/x-ownedunit-reinforcement"):
            data = event.mimeData()
            bstream = data.retrieveData("application/x-ownedunit-reinforcement", QtCore.QVariant.ByteArray)
            message = pickle.loads(bstream)
            if message["group"] != self.group:        
                event.accept()
                return

        event.ignore()
        
    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-ownedunit-reinforcement"):
            data = event.mimeData()
            bstream = data.retrieveData("application/x-ownedunit-reinforcement", QtCore.QVariant.ByteArray)
            message = pickle.loads(bstream)
            if message["group"] != self.group:        
                event.accept()
                return
        event.ignore()    

class ReinforcementWidget(FormClass, BaseClass):
    def __init__(self, parent, *args, **kwargs):
        logger.debug("GW Temporary item instantiating.")
        BaseClass.__init__(self, *args, **kwargs)
        
        self.setupUi(self)
        self.parent = parent

        self.reinforcementListWidget.setItemDelegate(ReinforcementDelegate(self))
        
        unitGroupsLayout = {}
        self.unitsGroup = {}

        unitGroupsLayout[0] = self.ownedGroup.layout()
        unitGroupsLayout[1] = self.group1.layout() 
        unitGroupsLayout[2] = self.group2.layout()
        unitGroupsLayout[3] = self.group3.layout()
        unitGroupsLayout[4] = self.group4.layout()
        unitGroupsLayout[5] = self.group5.layout()
        
        for i in range(0,6):
            self.unitsGroup[i] = groupListWidget(self, i)
            unitGroupsLayout[i].addWidget(self.unitsGroup[i])
        
        #self.group1ListWidget.setItemDelegate(ReinforcementGroupDelegate(self))
        
        self.parent.ReinforcementUpdated.connect(self.processReinforcementInfo)
        self.parent.ReinforcementsGroupDeleted.connect(self.removeGroup)
        self.parent.ReinforcementsGroupUpdated.connect(self.processReinforcementGroup)
        self.parent.playersListUpdated.connect(self.updatePlayerList)
        self.parent.creditsUpdated.connect(self.updateCreditsCheck)

        self.reinforcementListWidget.itemPressed.connect(self.itemPressed)

        self.reinforcements = {}
        
        self.poolOfUnits = {}
        
        #self.confirmGroupButton.clicked.connect(self.confirmGroup)
        self.buyBtn.clicked.connect(self.buyAll)
        self.offerBtn.clicked.connect(self.offer)
                
        self.currentMoneyCost = 0

        self.waitingForPlayerList = False


    def updatePlayerList(self, players):
        ''' update the player list for offering units'''
        if self.waitingForPlayerList:
            player, ok = QtGui.QInputDialog.getItem(self, "Select a player",
                "Give to:", sorted(players.keys()), 0, False)
            
            if ok and player:
                for uid in self.reinforcements:
                    if self.reinforcements[uid].owned != 0:
                        item = dict(unit=self.reinforcements[uid].uid, amount=self.reinforcements[uid].owned)
                        self.parent.send(dict(command="offer_reinforcement_group", giveTo=players[player], item=item))
                self.currentMoneyCost = 0        
                
            self.waitingForPlayerList = False

    def reset(self):
        ''' close the panel and reset all units'''
        self.currentMoneyCost = 0
        self.close()

    def offer(self):
        ''' send a message to the server about our nice offer'''

        self.parent.send(dict(command="get_player_list"))
        self.waitingForPlayerList = True

    def buyAll(self):
        ''' send a message to the server about our shopping list'''

        for uid in self.reinforcements:
            if self.reinforcements[uid].owned != 0:
                item = dict(unit=self.reinforcements[uid].uid, amount=self.reinforcements[uid].owned)
                self.parent.send(dict(command="buy_reinforcement_group", item=item))
            
        self.currentMoneyCost = 0

    def itemPressed(self, item):
        '''buy or unbuy an item'''
        if QtGui.QApplication.mouseButtons() == QtCore.Qt.LeftButton:
            if not item.disabled:
                if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier :
                    if self.currentMoneyCost + (item.price * 5) <= self.parent.credits:
                        item.add(5)
                else: 
                    if self.currentMoneyCost + item.price <= self.parent.credits:
                        item.add(1)        
        else:
            if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier :
                item.remove(5)
            else: 
                item.remove(1)              
        
        self.computeAllCosts()
        self.updateCreditsCheck()

    def updateCreditsCheck(self):
        '''disable item we can't buy'''
        for uid in self.reinforcements:
            if not self.reinforcements[uid].isHidden():
                if self.parent.credits - (self.currentMoneyCost) < self.reinforcements[uid].price:
                    self.reinforcements[uid].setDisabled()
                else:
                    self.reinforcements[uid].setEnabled()
                    
    def computeAllCosts(self):
        ''' compute the costs'''
        self.currentMoneyCost = 0
        for uid in self.reinforcements:
            if self.reinforcements[uid].owned != 0:
                self.currentMoneyCost = self.currentMoneyCost + (self.reinforcements[uid].price * self.reinforcements[uid].owned)  

        self.costText.setText("Cost : %i credits" % self.currentMoneyCost)
    
    def processReinforcementGroup(self, message):
        '''Handle a reinforcementGroup info message'''
        
        group = message["group"]
        uid = message["unit"]
        amount = message["amount"]
        

        if uid in self.reinforcements:
            infos = self.reinforcements[uid].getInfos()
            infos["owned"] = amount
   
        if uid not in self.unitsGroup[group].groupUnits:
            self.unitsGroup[group].groupUnits[uid] = ReinforcementItem(uid, small=True)
            self.unitsGroup[group].addItem(self.unitsGroup[group].groupUnits[uid])
            self.unitsGroup[group].groupUnits[uid].update(infos, self.parent)
        else:
            self.unitsGroup[group].groupUnits[uid].update(infos, self.parent)
  
    def removeGroup(self, message):
        ''' remove a whole group'''
        group = message["group"]
        self.unitsGroup[group].deleteAll()
        
        
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