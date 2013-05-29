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

FormClass, BaseClass = util.loadUiType("galacticwar/temporaryItems.ui")

class TemporaryWidget(FormClass, BaseClass):
    def __init__(self, parent, *args, **kwargs):
        logger.debug("GW Temporary item instantiating.")
        BaseClass.__init__(self, *args, **kwargs)
        
        self.setupUi(self)
        self.parent = parent

        self.reinforcementListWidget.setItemDelegate(ReinforcementDelegate(self))
        self.parent.temporaryReinforcementUpdated.connect(self.processReinforcementInfo)

        self.reinforcements = {}

    def processReinforcementInfo(self, message):
    	'''Handle a reinforcement info message'''
    	uid = message["uid"]
    	print message
    	if uid not in self.reinforcements:
            self.reinforcements[uid] = ReinforcementItem(uid)
            self.reinforcementListWidget.addItem(self.reinforcements[uid])
            self.reinforcements[uid].update(message, self.parent)
        else:
            self.reinforcements[uid].update(message, self.parent)