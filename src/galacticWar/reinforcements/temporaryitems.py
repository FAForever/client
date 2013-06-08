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
from temporaryReinforcementItem import ReinforcementItem, ReinforcementDelegate
import cPickle

FormClass, BaseClass = util.loadUiType("galacticwar/temporaryItems.ui")



class TemporaryWidget(FormClass, BaseClass):
    def __init__(self, parent, *args, **kwargs):
        logger.debug("GW Temporary item instantiating.")
        BaseClass.__init__(self, *args, **kwargs)
        
        self.setupUi(self)
        self.parent = parent

        self.reinforcementListWidget.setItemDelegate(ReinforcementDelegate(self))
        self.parent.planetaryDefenseUpdated.connect(self.processReinforcementInfo)
        self.parent.creditsUpdated.connect(self.updateCreditsCheck)
        
        #self.reinforcementListWidget.itemDoubleClicked.connect(self.buyItem)
        self.reinforcementListWidget.mouseMoveEvent = self.mouseMove
        self.reinforcements = {}

    def startDrag(self, event):
        ''' Draging building'''
        index = self.reinforcementListWidget.indexAt(event.pos())
        if not index.isValid():
            return

        ## selected is the relevant person object
        selected = self.reinforcementListWidget.model().data(index, QtCore.Qt.UserRole)   
        
        bstream = cPickle.dumps(selected)
        mimeData = QtCore.QMimeData()
        mimeData.setData("application/x-building-reinforcement", bstream)

        drag = QtGui.QDrag(self)
        drag.setMimeData(mimeData)
        
        drag.setPixmap(self.reinforcementListWidget.itemAt(event.pos()).icon().pixmap(50,50))
        
        drag.setHotSpot(QtCore.QPoint(0,0))
        drag.start(QtCore.Qt.MoveAction) 

    def mouseMove(self, event):
        ''' moving items'''
        self.startDrag(event)

    def buyItem(self, item):
        '''buy an item'''
        question = QtGui.QMessageBox.question(self,item.description, "Buy this item?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if question == QtGui.QMessageBox.Yes :
            self.parent.send(dict(command="buy_temporary_item", uid=item.uid))        

    def updateCreditsCheck(self, credits):
        '''disable item we can't buy'''
        for uid in self.reinforcements:
            if not self.reinforcements[uid].isHidden():
                if credits < self.reinforcements[uid].price:
                    self.reinforcements[uid].setDisabled()
                else:
                    self.reinforcements[uid].setEnabled()

    def processReinforcementInfo(self, message):
        '''Handle a reinforcement info message'''
        uid = message["uid"]
        if uid not in self.reinforcements:
            self.reinforcements[uid] = ReinforcementItem(uid)
            self.reinforcementListWidget.addItem(self.reinforcements[uid])
            self.reinforcements[uid].update(message, self.parent)
        else:
            self.reinforcements[uid].update(message, self.parent)
        
        self.updateCreditsCheck(self.parent.credits)