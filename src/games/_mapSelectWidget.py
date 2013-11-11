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




from PyQt4 import QtCore, QtGui

import util
from fa import maps

class MapItemDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, *args, **kwargs):
        QtGui.QStyledItemDelegate.__init__(self, *args, **kwargs)
        
    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
                
        painter.save()
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        
        icon = QtGui.QIcon(option.icon)
        iconsize = icon.actualSize(option.rect.size())
        
        #clear icon and text before letting the control draw itself because we're rendering these parts ourselves
        option.icon = QtGui.QIcon()        
        option.text = ""  
        option.widget.style().drawControl(QtGui.QStyle.CE_ItemViewItem, option, painter, option.widget)
        
        #Shadow
        painter.fillRect(option.rect.left()+8-1, option.rect.top()+8-1, iconsize.width(), iconsize.height(), QtGui.QColor("#202020"))

        #Icon
        icon.paint(painter, option.rect.adjusted(5-2, -2, 0, 0), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        
        #Description
        painter.translate(option.rect.left() + iconsize.width() + 10, option.rect.top()+10)
        clip = QtCore.QRectF(0, 0, option.rect.width()-iconsize.width() - 10 - 5, option.rect.height())
        html.drawContents(painter, clip)
  
        painter.restore()
        

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(MapItem.TEXTWIDTH)
        return QtCore.QSize(MapItem.ICONSIZE + MapItem.TEXTWIDTH + MapItem.PADDING, MapItem.ICONSIZE)  
    

class MapItem(QtGui.QListWidgetItem):
    TEXTWIDTH = 150
    ICONSIZE = 64
    PADDING = 10
    
    WIDTH = ICONSIZE + TEXTWIDTH
    
    def __init__(self, parent, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)
        
        self.parent         = parent
        self.uid            = None
        self.mapname        = None
        self.mapdisplayname = None
        self.client         = None

        self.setHidden(True)
 
    def update(self, message):  
        self.uid = message["idmap"]
        self.mapname = maps.link2name(message['maprealname'])  
        # Map preview code

        self.mapdisplayname = maps.getDisplayName(self.mapname)
        icon = maps.preview(self.mapname)
        if not icon:
            self.parent.downloader.downloadMap(self.mapname, self)
            icon = util.icon("games/unknown_map.png")

        self.setIcon(icon)
        text = "<font valign=center><b>%s</b></font>" % self.mapdisplayname
        self.setText(text)
        
        if message["selected"] == True:
            self.setSelected(True)

class mapSelectWidget(QtGui.QDialog):
    def __init__(self, parent, *args, **kwargs):
        
        QtGui.QDialog.__init__(self, *args, **kwargs)
        
        self.parent = parent
        self.client = self.parent.client
        
        self.setMinimumSize(640, 480)
        
        self.setWindowFlags( self.windowFlags() | QtCore.Qt.WindowMaximizeButtonHint )
        
        self.setWindowTitle ( "Selection of maps for the Matchmaker")
        
        
        self.group_layout   = QtGui.QVBoxLayout(self)
        
        self.listMaps       = QtGui.QListWidget(self)
        self.listMaps.setSelectionMode(2)
        self.listMaps.setWrapping(1)
        self.listMaps.setSpacing(5)
        self.listMaps.setResizeMode(1)
        self.listMaps.setSortingEnabled(1)        
        
        self.listMaps.setItemDelegate(MapItemDelegate(self))
              
        label = QtGui.QLabel("Your selection will be validated when you close this window.")
        
        self.group_layout.addWidget(self.listMaps)
        self.group_layout.addWidget(label)
        
        self.client.ladderMapsList.connect(self.mapList)
        self.setStyleSheet(self.parent.styleSheet())
        self.finished.connect(self.cleaning)

    def showEvent(self, event):
        self.client.statsServer.send(dict(command="ladder_maps", user=self.client.login))

    def mapList(self, msg):
        self.listMaps.clear()

        map_list = msg["values"]
        
        for map in map_list :
            item = MapItem(self.client)
            self.listMaps.addItem(item)
            item.update(map)
            

    
    def cleaning(self):
        mapSelected = []
        for item in self.listMaps.selectedItems():
            mapSelected.append(item.uid)

        self.client.send(dict(command="ladder_maps", maps=mapSelected))
        


        
        