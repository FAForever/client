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
from fa.game_version import GameVersion
import util

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

RANKED_SEARCH_EXPANSION_TIME = 10000 #milliseconds before search radius expands

SEARCH_RADIUS_INCREMENT = 0.05
SEARCH_RADIUS_MAX = 0.25

FormClass, BaseClass = util.loadUiType("games/host.ui")


class HostgameWidget(FormClass, BaseClass):
    def __init__(self, parent, item, versions, allow_map_choice):
        BaseClass.__init__(self)

        logger.info("HostGameWidget started with: ")
        logger.info(versions)
        logger.info(allow_map_choice)
        self.setupUi(self)
        self.parent = parent
        
        self.parent.options = []

        self.setStyleSheet(self.parent.client.styleSheet())
        
        self.setWindowTitle("Host Game: " + item.name)
        self.titleEdit.setText(self.parent.gamename)
        self.passEdit.setText(self.parent.gamepassword)
        self.game = GameItem(0)
        self.gamePreview.setItemDelegate(GameItemDelegate(self))
        self.gamePreview.addItem(self.game)

        self.message = {}
        self.message['title'] = self.parent.gamename
        self.message['host'] = self.parent.client.login
        self.message['teams'] = {1:[self.parent.client.login]}
#        self.message.get('access', 'public')
        self.message['featured_mod'] = "faf"
        self.message['mapname'] = self.parent.gamemap
        self.message['state'] = "open"
        
        self.game.update(self.message, self.parent.client)


        self.versions = versions
        self.selectedVersion = 0
        for version in versions:
            self.versionList.addItem(version['name'], version['id'])

        self.versionList.currentIndexChanged.connect(self.versionChanged)

        i = 0
        index = 0
        if allow_map_choice:
            allmaps = dict()
            for map in maps.maps.keys() + maps.getUserMaps():
                allmaps[map] = maps.getDisplayName(map)
            for (map, name) in sorted(allmaps.iteritems(), key=lambda x: x[1]):
                if map == self.parent.gamemap:
                    index = i
                self.mapList.addItem(name, map)
                i = i + 1
            self.mapList.setCurrentIndex(index)
        else:
            self.mapList.hide()
            
        icon = maps.preview(self.parent.gamemap, True)

        if not icon:
            icon = util.icon("games/unknown_map.png", False, True)
                

        self.mods = {}
        #this makes it so you can select every non-ui_only mod
        for mod in modvault.getInstalledMods():
            if mod.ui_only:
                continue
            self.mods[mod.totalname] = mod
            self.modList.addItem(mod.totalname)

        names = [mod.totalname for mod in modvault.getActiveMods(uimods=False)]
        logger.debug("Active Mods detected: %s" % str(names))
        for name in names:
            l = self.modList.findItems(name, QtCore.Qt.MatchExactly)
            logger.debug("found item: %s" % l[0].text())
            if l: l[0].setSelected(True)
            
        #self.mapPreview.setPixmap(icon)
        
        self.mapList.currentIndexChanged.connect(self.mapChanged)
        self.hostButton.released.connect(self.hosting)
        self.titleEdit.textChanged.connect(self.updateText)

    @property
    def game_version(self):
        return GameVersion("FAForever/"+self.gameVersion.repo_name)

    @property
    def selected_mods(self):
        return [self.mods[str(m.text())] for m in self.modList.selectedItems()]

    def versionChanged(self, index):
        self.selectedVersion = index
        
    def updateText(self, text):
        self.message['title'] = text
        self.game.update(self.message, self.parent.client)

    def hosting(self):
        self.parent.saveGameName(self.titleEdit.text().strip())
        self.parent.saveGameMap(self.parent.gamemap)
        if self.passCheck.isChecked():
            self.parent.ispassworded = True
            self.parent.savePassword(self.passEdit.text())
        else:
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

