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
from galacticWar import FACTIONS
import util

FormClass, BaseClass = util.loadUiType("galacticwar/options.ui")

        

class GWOptions(FormClass, BaseClass):
    def __init__(self, parent, *args, **kwargs):
        logger.debug("GW options instantiating.")
        BaseClass.__init__(self, *args, **kwargs)
        
        self.setupUi(self)
        self.parent = parent
        
         
        self.rotation = True
        self.AA = True

        self.mapTransparencySlider.setTracking(False)
        self.mapTransparencySlider.valueChanged.connect(self.Updatetransparency)
        
        self.starsSlider.setTracking(False)
        self.starsSlider.valueChanged.connect(self.updateStars)

        
        self.uefColor.pressed.connect(lambda : self.pickColor(0, self.uefColor))
        self.aeonColor.pressed.connect(lambda : self.pickColor(1, self.aeonColor))
        self.cybranColor.pressed.connect(lambda : self.pickColor(2, self.cybranColor))
        self.seraphimColor.pressed.connect(lambda : self.pickColor(3, self.seraphimColor))
        
        self.colorResetButton.pressed.connect(self.resetColors)
        
        self.rotationcheckBox.clicked.connect(self.updateRotation)
        self.AAcheckBox.clicked.connect(self.updateAA)
    
    def updateStars(self, value):
        if hasattr(self.parent,"OGLdisplay"):
            self.parent.stars = value
            
            self.parent.OGLdisplay.starField()
            self.parent.OGLdisplay.galaxyStarsFront = self.parent.OGLdisplay.drawStars(0)
            self.parent.OGLdisplay.galaxyStarsBack = self.parent.OGLdisplay.drawStars(1)            
            util.settings.beginGroup("GalacticWar")
            util.settings.setValue("map/stars", value)
            util.settings.endGroup()            
    
    def updateAA(self, state):
        util.settings.beginGroup("GalacticWar")
        if state :
            util.settings.setValue("display/AA", "true")
        else :
            util.settings.setValue("display/AA", "false")
        util.settings.endGroup()
            
    def updateRotation(self, state):        
        if hasattr(self.parent,"OGLdisplay"):
            util.settings.beginGroup("GalacticWar")
            if state :
                self.parent.rotation = True
                util.settings.setValue("map/planetRotation", "true")
                self.parent.OGLdisplay.timerRotate.start(self.parent.OGLdisplay.UPDATE_ROTATION)
            else :
                self.parent.rotation = False
                util.settings.setValue("map/planetRotation", "false")
                self.parent.OGLdisplay.timerRotate.stop()
            util.settings.endGroup()        
            
    def pickColor(self, faction, button):
        color = QtGui.QColorDialog.getColor(self.parent.COLOR_FACTIONS[faction], self)
        if color.isValid(): 
            qss = "background-color: %s" % color.name()
            button.setStyleSheet(qss) 

            util.settings.beginGroup("GalacticWar")
            util.settings.setValue("factionColors/%s" % FACTIONS[faction], color)
            util.settings.endGroup()
            
            self.parent.COLOR_FACTIONS[faction] = color
            self.parent.galaxy.updateAllSites()
            self.parent.OGLdisplay.createZones()

    def resetColors(self):
        self.parent.COLOR_FACTIONS[0] = QtGui.QColor(0,0,255)
        self.parent.COLOR_FACTIONS[1] = QtGui.QColor(0,255,0)
        self.parent.COLOR_FACTIONS[2] = QtGui.QColor(255,0,0)
        self.parent.COLOR_FACTIONS[3] = QtGui.QColor(255,255,0)
        
            
        util.settings.beginGroup("GalacticWar")
        for faction in range(4):
            util.settings.setValue("factionColors/%s" % FACTIONS[faction], self.parent.COLOR_FACTIONS[faction])
        util.settings.endGroup()
        
        self.colorButtons()
        
        self.parent.galaxy.updateAllSites()
        self.parent.OGLdisplay.createZones()            


    def Updatetransparency(self, value):
        if hasattr(self.parent,"OGLdisplay"): 
            self.parent.mapTransparency = value
            self.parent.OGLdisplay.createZones()
            util.settings.beginGroup("GalacticWar")
            util.settings.setValue("map/transparency", value)
            util.settings.endGroup()
        
    def loadSettings(self):
        print "loading settings"
        util.settings.beginGroup("GalacticWar")
        self.parent.mapTransparency = int(util.settings.value("map/transparency", 10))
        self.parent.stars = int(util.settings.value("map/stars", 25))
        self.parent.COLOR_FACTIONS[0] = (util.settings.value("factionColors/uef", QtGui.QColor(0,0,255)))
        self.parent.COLOR_FACTIONS[1] = (util.settings.value("factionColors/aeon", QtGui.QColor(0,255,0)))
        self.parent.COLOR_FACTIONS[2] = (util.settings.value("factionColors/cybran", QtGui.QColor(255,0,0)))
        self.parent.COLOR_FACTIONS[3] = (util.settings.value("factionColors/seraphim", QtGui.QColor(255,255,0)))
        self.parent.AA = (util.settings.value("display/AA", "true") == "true")
        self.parent.rotation = (util.settings.value("map/planetRotation", "true") == "true")
        
        self.rotationcheckBox.setChecked(self.parent.rotation)
        self.AAcheckBox.setChecked(self.parent.AA)

        util.settings.endGroup()        
        self.mapTransparencySlider.setValue(self.parent.mapTransparency)
        self.starsSlider.setValue(self.parent.stars)
        self.colorButtons()
    
    def colorButtons(self):
        qss = "background-color: %s" % self.parent.COLOR_FACTIONS[0].name()
        self.uefColor.setStyleSheet(qss)    
        qss = "background-color: %s" % self.parent.COLOR_FACTIONS[1].name()
        self.aeonColor.setStyleSheet(qss)    
        qss = "background-color: %s" % self.parent.COLOR_FACTIONS[2].name()
        self.cybranColor.setStyleSheet(qss)    
        qss = "background-color: %s" % self.parent.COLOR_FACTIONS[3].name()
        self.seraphimColor.setStyleSheet(qss)                                        


      