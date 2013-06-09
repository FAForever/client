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



import urllib2
import tempfile
import zipfile

from PyQt4 import QtCore, QtGui

import modvault
from util import datetostr,strtodate,now
import util

FormClass, BaseClass = util.loadUiType("modvault/upload.ui")


class UploadModWidget(FormClass, BaseClass):
    def __init__(self, parent, modDir, modinfo, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)       

        self.setupUi(self)
        self.parent = parent
        self.client = self.parent.client
        self.modinfo = modinfo
        self.modDir = modDir
        
        self.setStyleSheet(self.parent.client.styleSheet())
        
        self.setWindowTitle("Uploading Mod")

        self.Name.setText(modinfo["name"])
        self.Version.setText(str(modinfo["version"]))
        self.UIOnly.setChecked(modinfo["ui_only"] == "true")
        self.UID.setText(modinfo["uid"])
        self.Description.setPlainText(modinfo["description"])
        self.Thumbnail.setPixmap(util.pixmap("games/unknown_map.png"))

        self.IconURI.returnPressed.connect(self.updateThumbnail)
        self.UploadButton.pressed.connect(self.upload)
        self.IconDialogButton.pressed.connect(self.openicondialog)

    @QtCore.pyqtSlot()
    def upload(self):
        n = self.Name.text()
        if ('"' in n or '<' in n or '*' in n or '>' in n or '|' in n or '?' in n
            or '/' in n or '\\' in n or ':' in n):
            QtGui.QMessageBox.information(self.client,"Invalid Name",
                        "The mod name contains invalid characters: /\\<>|?:\"")
            return
        if n in [m.title for  m in self.parent.mods]:
            QtGui.QMessageBox.information(self.client,"Name in Use",
                        "There is already a mod with this name")
            return
        if self.UID.text() in [m.uid for m in self.parent.mods]:
            QtGui.QMessageBox.information(self.client,"UID in Use",
                        "There is already a mod with this UID")
            return
        try:
            temp = tempfile.NamedTemporaryFile(mode='w+b', suffix=".zip", delete=False)
            zipped = zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED)
            zipdir(self.modDir, zipped)
            zipped.close()
            temp.flush()
        except:
            QtGui.QMessageBox.critical(self.client, "Mod uploading error", "Something went wrong zipping the mod files.")
            return None
        qfile =QtCore.QFile(temp.name)
        self.modinfo["big"] = (self.SizeType.getIndex() == 1)
        self.modinfo["small"] = (self.SizeType.getIndex() == 2)
        self.modinfo["date"] = datetostr(now())
        self.modinfo["last_updated"] = self.modinfo["date"]
        #The server should check again if there is already a mod with this name.
        self.client.writeToServer("UPLOAD_MOD", self.modinfo["name"] + ".zip", self.modinfo, qfile)
        
    
    @QtCore.pyqtSlot()
    def openicondialog(self):
        iconfilename = QtGui.QFileDialog.getOpenFileName(self.client, "Select an icon file", self.modDir,"Image files (*.png|*.jpg|*jpeg)")
        if iconfilename == "": return
        try:
            self.Thumbnail.setPixmap(util.icon(iconfilename))
        except:
            QtGui.QMessageBox.information(self.client,"Invalid Icon FIle",
                        "This was not a valid icon file. Please pick a png or jpeg")
            return
        self.IconURI.setText(iconfilename)
        
    @QtCore.pyqtSlot()
    def updateThumbnail(self):
        try:
            self.Thumbnail.setPixmap(util.icon(self.IconURI.text()))
        except:
            QtGui.QMessageBox.information(self.client,"Invalid Icon FIle",
                        "This was not a valid icon file. Please pick a png or jpeg")
    

#from http://stackoverflow.com/questions/1855095/how-to-create-a-zip-archive-of-a-directory-in-python
def zipdir(path, zipf):
    for root, dirs, files in os.walk(path):
        for f in files:
            zipf.write(os.path.join(root, f))

