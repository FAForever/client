#-------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
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

from PyQt4 import QtCore, QtGui, QtWebKit

VIDEO = QtCore.QUrl('http://91.121.153.175/faf/intro.mp4')

import util


class gwSelectFaction(QtGui.QWizard):
    def __init__(self, parent=None):
        
        super(gwSelectFaction, self).__init__(parent)

        self.parent = parent
        self.client = parent.client
        
        self.selectedFaction = None

        self.webview = QtWebKit.QWebView()
        QtWebKit.QWebSettings.globalSettings().setAttribute(QtWebKit.QWebSettings.PluginsEnabled, True)    

        self.addPage(IntroPage(self))
        self.addPage(selectFactionPage(self))
        self.addPage(factionSelected(self))

        #self.cleanupPage.connect(self.cleaningPage)

        self.setWizardStyle(QtGui.QWizard.ModernStyle)

        self.setPixmap(QtGui.QWizard.BannerPixmap,
                QtGui.QPixmap('client/banner.png'))
        self.setPixmap(QtGui.QWizard.BackgroundPixmap,
                QtGui.QPixmap('client/background.png'))

        self.setWindowTitle("Create Account")

class IntroPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(IntroPage, self).__init__(parent)
        self.setTitle("Introduction")

        
        self.parent = parent
        self.parent.webview.setUrl(VIDEO)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.parent.webview)
        
        self.setLayout(layout)      

    def validatePage(self):
        return True

class selectFactionPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(selectFactionPage, self).__init__(parent)
        
        self.parent = parent
        self.client = parent.client

        self.setTitle("Faction selection")
        
        layout = QtGui.QVBoxLayout()
        label = QtGui.QLabel("Hi commander. <br><br>The war is raging through the galaxy.<br>You have to pick a side !")
        
        
        layoutFactions = QtGui.QHBoxLayout()
        
        Aeon = QtGui.QPushButton()
        Cybran = QtGui.QPushButton()
        Seraphim = QtGui.QPushButton()
        UEF = QtGui.QPushButton()

        Aeon.setIconSize(QtCore.QSize(60,60))
        Cybran.setIconSize(QtCore.QSize(60,60))
        Seraphim.setIconSize(QtCore.QSize(60,60))
        UEF.setIconSize(QtCore.QSize(60,60))

        UEF.setMaximumSize(100, 100)
        Aeon.setMaximumSize(100, 100)
        Seraphim.setMaximumSize(100, 100)
        Cybran.setMaximumSize(100, 100)
        
        UEF.setMinimumSize(100, 100)
        Aeon.setMinimumSize(100, 100)
        Seraphim.setMinimumSize(100, 100)
        Cybran.setMinimumSize(100, 100)
        
        Aeon.setFlat(1)
        Cybran.setFlat(1)
        Seraphim.setFlat(1)
        UEF.setFlat(1)
        
        Aeon.setIcon(util.icon("games/automatch/aeon.png"))
        Cybran.setIcon(util.icon("games/automatch/cybran.png"))
        Seraphim.setIcon(util.icon("games/automatch/seraphim.png"))
        UEF.setIcon(util.icon("games/automatch/uef.png"))
            
        layoutFactions.addWidget(UEF)
        layoutFactions.addWidget(Aeon)
        layoutFactions.addWidget(Cybran)        
        layoutFactions.addWidget(Seraphim)
        
        UEF.pressed.connect(self.uef)
        Aeon.pressed.connect(self.aeon)
        Cybran.pressed.connect(self.cybran)
        Seraphim.pressed.connect(self.seraphim)

        label2 = QtGui.QLabel("Be careful ! Once you have confirmed your allegiance to a faction, you won't be able to change it !")
        label2.setWordWrap(True)

        layout.addWidget(label)
        layout.addLayout(layoutFactions)
        layout.addWidget(label2)
        self.setLayout(layout)
        
    def uef(self):
        self.parent.selectedFaction = 0
        self.parent.next()

    def aeon(self):
        self.parent.selectedFaction = 1
        self.parent.next()
        
    def cybran(self):
        self.parent.selectedFaction = 2
        self.parent.next()
       
       
    def seraphim(self):
        self.parent.selectedFaction = 3
        self.parent.next()        
        
    def validatePage(self):       
        if self.parent.selectedFaction == None :
            return False
        return True
        
class factionSelected(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(factionSelected, self).__init__(parent)
        
        self.parent = parent
        

    def initializePage(self):
        if self.parent.selectedFaction == 0 :
            self.setTitle("Welcome to the United Earth Federation Army !<br><br>You can still alter your choice.<br>Once you've clicked finished, there is no going back !")
            self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("client/account_watermark_intro.png"))
        elif self.parent.selectedFaction == 1 :
            self.setTitle("You have embraced the Way.<br><br>You can still alter your choice.<br>Once you've clicked finished, there is no going back !")
            self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("client/account_watermark_created.png"))
        elif self.parent.selectedFaction == 2 :
            self.setTitle("You have been integrated to the symbiont network.<br><br>You can still alter your choice.<br>Once you've clicked finished, there is no going back !")
            self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("client/account_watermark_input.png"))
        elif self.parent.selectedFaction == 3 :
            self.setTitle("[Language Not Recognized]<br><br>You can still alter your choice.<br>Once you've clicked finished, there is no going back !")
            self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("client/account_seraphim.png"))

    def validatePage(self):    
        self.parent.parent.faction = self.parent.selectedFaction
        return True 