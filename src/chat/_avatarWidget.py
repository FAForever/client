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
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest

import base64, zlib, os
import util

class avatarWidget(QtGui.QDialog):
    def __init__(self, parent, user, *args, **kwargs):
        
        QtGui.QDialog.__init__(self, *args, **kwargs)
        
        self.user = user
        self.parent = parent
        
        self.setStyleSheet(self.parent.styleSheet())
        self.setWindowTitle ( "Avatar manager" )
        
        self.parent.requestAvatars()
        self.group_layout   = QtGui.QVBoxLayout(self)
        self.listAvatars    = QtGui.QListWidget()
         
        self.listAvatars.setWrapping(1)
        self.listAvatars.setSpacing(5)
        self.listAvatars.setResizeMode(1)


        self.addAvatarButton = QtGui.QPushButton("Add/Edit avatar")
        self.addAvatarButton.clicked.connect(self.addAvatar)
        
        self.group_layout.addWidget(self.listAvatars)
        self.group_layout.addWidget(self.addAvatarButton)

        self.item = []
        self.parent.avatarList.connect(self.avatarList)
    
        self.nams = {}
        self.avatars = {}
        

    def addAvatar(self):
        
        options = QtGui.QFileDialog.Options()       
        options |= QtGui.QFileDialog.DontUseNativeDialog
        
        fileName = QtGui.QFileDialog.getOpenFileName(self,
                "Select the PNG file",
                "",
                "png Files (*.png)", options)
        if fileName:
            ## check the properties of that file
            pixmap = QtGui.QPixmap(fileName)
            if pixmap.height() == 20 and pixmap.width() == 40 :
                
                text, ok = QtGui.QInputDialog.getText(self, "Avatar description",
                "Please enter the tooltip :", QtGui.QLineEdit.Normal, "")
                
                if ok and text != '':
                
                    file = QtCore.QFile(fileName)
                    file.open(QtCore.QIODevice.ReadOnly)
                    fileDatas = base64.b64encode(zlib.compress(file.readAll()))
                    file.close()
                
                    self.parent.send(dict(command="avatar", action="upload_avatar", name=os.path.basename(fileName),description=text, file=fileDatas))
                    
                
            else :
                QtGui.QMessageBox.warning(self, "Bad image", "The image must be in png, format is 40x20 !")      
        
            #self.client.send(dict(command="edits", action="submit", file = fileDatas))        

    def finishRequest(self, reply):

        if reply.url().toString() in self.avatars :
            img = QtGui.QImage()
            img.loadFromData(reply.readAll())
            pix = QtGui.QPixmap(img)
            self.avatars[reply.url().toString()].setIcon(QtGui.QIcon(pix))   
            self.avatars[reply.url().toString()].setIconSize(pix.rect().size())     
        
            util.addrespix(reply.url().toString(), QtGui.QPixmap(img))
    
    def clicked(self):
        self.parent.addAvatar(self.user, None)
        self.close()
        
    def create_connect(self, x):
        return lambda: self.doit(x)
    
    def doit(self, val):
        self.parent.addAvatar(self.user, val)
        self.close()
    
    def avatarList(self, avatar_list):
        
        button = QtGui.QPushButton()
        #self.group_layout.addWidget(button)
        self.avatars["None"] = button
        
        item = QtGui.QListWidgetItem()
        item.setSizeHint (QtCore.QSize(40,20))

        self.item.append(item)
            
        self.listAvatars.addItem (item )
        self.listAvatars.setItemWidget ( item, button )
        
        button.clicked.connect(self.clicked)
        
        for avatar in avatar_list :
            
            avatarPix = util.respix(avatar["url"])
            button = QtGui.QPushButton()

            button.clicked.connect(self.create_connect(avatar["url"]))
            
            item = QtGui.QListWidgetItem()
            item.setSizeHint (QtCore.QSize(40,20))
            self.item.append(item)
            
            self.listAvatars.addItem (item )
            

            button.setToolTip(avatar["tooltip"])
            url = QtCore.QUrl(avatar["url"])            
            self.avatars[avatar["url"]] = button
            
            self.listAvatars.setItemWidget ( item, self.avatars[avatar["url"]] )
            
            if not avatarPix :          
                self.nams[url] = QNetworkAccessManager(button)
                self.nams[url].finished.connect(self.finishRequest)
                self.nams[url].get(QNetworkRequest(url))
            else :
                self.avatars[avatar["url"]].setIcon(QtGui.QIcon(avatarPix))   
                self.avatars[avatar["url"]].setIconSize(avatarPix.rect().size())           

        
        
        