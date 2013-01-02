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

FormClass, BaseClass = util.loadUiType("featuredmods/featuredmods.ui")

class FeaturedModsWidget(FormClass, BaseClass):
    def __init__(self, client, *args, **kwargs):
        
        BaseClass.__init__(self, *args, **kwargs)        
        
        self.setupUi(self)

        self.client = client
        
        self.currentMod     = None
        self.modFiles       = None
        self.versionFiles   = None

        
        self.client.featuredModManager.connect(self.manageMod)
        self.client.featuredModManagerInfo.connect(self.manageModInfo)
        
        self.filesTable.cellPressed.connect(self.fileClicked)
        
        self.filesTable.horizontalHeader().setStretchLastSection ( True )
        self.versionTable.horizontalHeader().setStretchLastSection ( True )
        
        self.setStyleSheet(self.client.styleSheet())
        
        
    def updateTitle(self):
        self.title.setText("MOD MANAGER : %s" % self.currentMod)
        self.setWindowTitle("MOD MANAGER : %s" % self.currentMod)

    
    
    def fileClicked(self, row, col):
        if QtGui.QApplication.mouseButtons() != QtCore.Qt.RightButton:
            return            
        
        menu = QtGui.QMenu(self.filesTable)
        
        
        actionView = QtGui.QAction("View Update Files", menu)
        actionAdd = QtGui.QAction("Add File", menu)
        # Adding to menu
        menu.addAction(actionView)
        menu.addAction(actionAdd)            
        
        # Triggers
        actionView.triggered.connect(lambda: self.viewUpdatesFiles(row+1))
        #actionAdd.triggered.connect()
        
        #Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())

    def viewUpdatesFiles(self, uid):
        self.versionTable.clear()
        self.versionTable.setHorizontalHeaderItem(0, QtGui.QTableWidgetItem("version"))
        self.versionTable.setHorizontalHeaderItem(1, QtGui.QTableWidgetItem("filename"))
                
        i = 0
        for f in self.versionFiles :
            if f["fileuid"] == uid :
                itemFile = QtGui.QTableWidgetItem (f["name"])
                itemVersion = QtGui.QTableWidgetItem (str(f["version"]))
                
                #self.filesTable.insertRow(uid)
                self.versionTable.setRowCount ( i+1 )
                self.versionTable.setItem ( i, 0, itemVersion )
                self.versionTable.setItem ( i, 1, itemFile ) 
                i = i + 1               
    
    def updateModFiles(self):
        ## Clearing both table
        self.filesTable.clear()
        self.versionTable.clear()
        
        self.filesTable.setHorizontalHeaderItem(0, QtGui.QTableWidgetItem("path"))
        self.filesTable.setHorizontalHeaderItem(1, QtGui.QTableWidgetItem("filename"))
        
        self.versionTable.setHorizontalHeaderItem(0, QtGui.QTableWidgetItem("version"))
        self.versionTable.setHorizontalHeaderItem(1, QtGui.QTableWidgetItem("filename"))
        
        
        self.filesTable.setRowCount(len(self.modFiles))
        for f in self.modFiles :
            itemFile = QtGui.QTableWidgetItem (f["filename"])
            itemPath = QtGui.QTableWidgetItem (f["path"])
            uid = f["uid"] - 1
            #self.filesTable.insertRow(uid)
            self.filesTable.setItem ( uid, 0, itemPath )
            self.filesTable.setItem ( uid, 1, itemFile )
            
        
            
    
    
    def manageModInfo(self, message):
        print message
        self.currentMod = message["mod"]
        self.modFiles       = message["mod_files"]
        self.versionFiles   = message["version_files"] 
        self.updateTitle()
        self.updateModFiles()

        
    def manageMod(self, mod):
        self.currentMod = mod
        self.updateTitle()        
        self.show()
        
        # asking for mod info
        self.client.send(dict(command="mod_manager_info", action="list", mod=self.currentMod))