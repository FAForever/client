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
import cPickle

FormClass, BaseClass = util.loadUiType("galacticwar/reinforcementItems.ui")



class ReinforcementWidget(FormClass, BaseClass):
    def __init__(self, parent, *args, **kwargs):
        logger.debug("GW Temporary item instantiating.")
        BaseClass.__init__(self, *args, **kwargs)
        
        self.setupUi(self)
        self.parent = parent

        self.reinforcementListWidget.setItemDelegate(ReinforcementDelegate(self))
        self.parent.ReinforcementUpdated.connect(self.processReinforcementInfo)
        self.parent.creditsUpdated.connect(self.updateCreditsCheck)
        
        self.reinforcementListWidget.itemPressed.connect(self.itemPressed)
        #self.reinforcementListWidget.mouseMoveEvent = self.mouseMove
        self.reinforcements = {}
        
        
        self.confirmGroupButton.clicked.connect(self.confirmGroup)
        
        self.groups = []
        
        self.groupsWidgets.itemPressed.connect(self.myGroupsPressed)
        
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
        actionDelete.triggered.connect(lambda : self.deleteGroup(item.index))
 
        # Adding to menu
        menu.addAction(actionDelete)

        #Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())        
        
    def deleteGroup(self, index):
        '''Delete a group'''
        
        groupPrice = 0
        for item in self.groups[index]:
            groupPrice = groupPrice + (item["price"] * item["amount"])
                
        self.currentMoneyCost = self.currentMoneyCost - groupPrice
        self.groups.pop(index)
        
        # update the interface
        self.computeAllCosts() 
        self.updateGroupTree()
        self.updateCreditsCheck()
        


#    def startDrag(self, event):
#        ''' Draging building'''
#        index = self.reinforcementListWidget.indexAt(event.pos())
#        if not index.isValid():
#            return
#
#        ## selected is the relevant person object
#        selected = self.reinforcementListWidget.model().data(index, QtCore.Qt.UserRole)   
#        
#        bstream = cPickle.dumps(selected)
#        mimeData = QtCore.QMimeData()
#        mimeData.setData("application/x-building-reinforcement", bstream)
#
#        drag = QtGui.QDrag(self)
#        drag.setMimeData(mimeData)
#        
#        drag.setPixmap(self.reinforcementListWidget.itemAt(event.pos()).icon().pixmap(50,50))
#        
#        drag.setHotSpot(QtCore.QPoint(0,0))
#        drag.start(QtCore.Qt.MoveAction) 

#    def mouseMove(self, event):
#        ''' moving items'''
#        self.startDrag(event)

    def confirmGroup(self):
        '''add this group'''
        
        group = []
        
        for uid in self.reinforcements:
            if self.reinforcements[uid].owned != 0:
                group.append(dict(uid=uid, amount=self.reinforcements[uid].owned, name=self.reinforcements[uid].name, price = self.reinforcements[uid].price, delay = self.reinforcements[uid].delay))
        
        if len(group) == 0:
            return
        
        self.currentMoneyCost = self.currentMoneyCost + self.currentGroupMoneyCost
        
        
        self.groups.append(group)
        
        #clear the current group buy
        for uid in self.reinforcements:
            self.reinforcements[uid].owned = 0
        
        self.computeAllCosts()
        self.updateCreditsCheck()
        
        self.updateGroupTree()
        
    def updateGroupTree(self):
        '''Update the group tree'''
        self.groupsWidgets.clear()
        if len(self.groups) == 0:
            return
        i = 0
        for group in self.groups:
            group_item = QtGui.QTreeWidgetItem()
            
            price = 0
            delay = 0
            for item in group:

                formation_item = QtGui.QTreeWidgetItem()
                formation_item.index = i
                totPrice = item["price"] * item["amount"]
                formation_item.setText(0,"%s x%i (%i credits)" % (item["name"], item["amount"], totPrice))

                price = price + totPrice 
                delay = delay + item["delay"] * item["amount"]
            
                group_item.addChild(formation_item)

            group_item.setText(0, "Group %i : %i credits, %0.1f minutes delay" % (i+1, price, delay))
            group_item.index = i
            self.groupsWidgets.addTopLevelItem(group_item)
            group_item.setExpanded(True)
            i=i+1
                
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