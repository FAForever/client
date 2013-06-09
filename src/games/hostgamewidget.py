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



import os

from PyQt4 import QtCore, QtGui
from games.gameitem import GameItem, GameItemDelegate
import modvault

from fa import maps
import util

import logging
logger = logging.getLogger("faf.hostgamewidget")
logger.setLevel(logging.DEBUG)

RANKED_SEARCH_EXPANSION_TIME = 10000 #milliseconds before search radius expands

SEARCH_RADIUS_INCREMENT = 0.05
SEARCH_RADIUS_MAX = 0.25

FormClass, BaseClass = util.loadUiType("games/host.ui")


class HostgameWidget(FormClass, BaseClass):
    def __init__(self, parent, item, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)       

        self.setupUi(self)
        self.parent = parent
        
        self.parent.options = []

        if len(item.options) == 0 :   
            self.optionGroup.setVisible(False)
        else :
            group_layout = QtGui.QVBoxLayout()
            self.optionGroup.setLayout(group_layout)
            
            for option in item.options :
                checkBox = QtGui.QCheckBox(self)
                checkBox.setText(option)
                checkBox.setChecked(True)
                group_layout.addWidget(checkBox)
                self.parent.options.append(checkBox)
        
        self.modList.setItemDelegate(ModItemDelegate(self))
        self.setStyleSheet(self.parent.client.styleSheet())
        
        self.setWindowTitle ( "Hosting Game : " + item.name )
        self.titleEdit.setText ( self.parent.gamename )
        self.passEdit.setText ( self.parent.gamepassword )
        self.game = GameItem(0)
        self.gamePreview.setItemDelegate(GameItemDelegate(self));
        self.gamePreview.addItem(self.game)
        
        self.message = {}
        self.message['title'] = self.parent.gamename
        self.message['host'] = self.parent.client.login
        self.message['teams'] = {1:[self.parent.client.login]}
#        self.message.get('access', 'public')
        self.message['featured_mod'] = item.mod
        self.message['mapname'] = self.parent.gamemap
        self.message['state'] = "open"
        
        self.game.update(self.message, self.parent.client)
        
        i = 0
        index = 0
        
        for map in maps.maps :
            name = maps.getDisplayName(map)
            if map == self.parent.gamemap :
                index = i
            self.mapList.addItem(name, map)
            i = i + 1

        for map in maps.getUserMaps() :
            name = maps.getDisplayName(map)
            if map == self.parent.gamemap :
                index = i
            self.mapList.addItem(name, map)
            i = i + 1
        
        self.mapList.setCurrentIndex(index)
        
        icon = maps.preview(self.parent.gamemap, True)
        if not icon:
            icon = util.icon("games/unknown_map.png", False, True)

        self.mods = []
        #this makes it so you can select every non-ui_only mod
        for mod in modvault.getInstalledMods(): #list of strings
            d = modvault.getModfromName(mod)
            if d == None or d["ui_only"]:
                continue
            m = ModItem(mod, d)
            self.modList.addItem(m)
            self.mods.append(m) # for easier manipulation of the items

        uids = [mod['name'] for mod in modvault.getActiveMods(uimods=False)]
        for m in self.mods:
            if m.uid in uids:
                m.setSelected(True)

        #self.mapPreview.setPixmap(icon)
        
        self.mapList.currentIndexChanged.connect(self.mapChanged)
        self.hostButton.released.connect(self.hosting)
        self.titleEdit.textChanged.connect(self.updateText)
        self.modList.itemClicked.connect(self.modclicked)
        
    def updateText(self, text):
        self.message['title'] = text
        self.game.update(self.message, self.parent.client)

    def hosting(self):
        self.parent.saveGameName(self.titleEdit.text().strip())
        self.parent.saveGameMap(self.parent.gamemap)
        if self.passCheck.isChecked() :
            self.parent.ispassworded = True
            self.parent.savePassword(self.passEdit.text())
        else :
            self.parent.ispassworded = False
        self.done(1)

    def mapChanged(self, index):
        self.parent.gamemap = self.mapList.itemData(index)
        icon = maps.preview(self.parent.gamemap, True)
        if not icon:
            icon = util.icon("games/unknown_map.png", False, True)
        #self.mapPreview.setPixmap(icon)        
        self.message['mapname'] = self.parent.gamemap
        self.game.update(self.message, self.parent.client)

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def modclicked(self, item):
        item.setSelected(not item.isSelected())
        logger.debug("mod %s clicked" % item.name)

class ModItemDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, *args, **kwargs):
        QtGui.QStyledItemDelegate.__init__(self, *args, **kwargs)

    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
                
        painter.save()
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        
        #Description
        painter.translate(option.rect.left() + 2, option.rect.top()+1)
        clip = QtCore.QRectF(0, 0, option.rect.width() - 8, option.rect.height())
        html.drawContents(painter, clip)
  
        painter.restore()
        

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(300)
        return QtCore.QSize(300, 20)  

        

class ModItem(QtGui.QListWidgetItem):
    def __init__(self, modstr, info, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.modstr = modstr
        self.__dict__.update(info)

        self.setText(self.modstr)
        self.setToolTip(self.description)
        self.setHidden(False)

    def __ge__(self, other):
        return not self.__lt__(self, other)

    def __lt__(self, other):
        return self.modstr.lower() < other.modstr.lower()
