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

"""
Modvault database documentation:
command = "modvault"
possible commands (value for the 'type' key):
    start: <no args> - given when the tab is opened. Signals that the server should send the possible mods.
    addcomment: moduid=<uid of the mod the comment belongs to>, comment={"or","uid","date","text"} 
    addbugreport: moduid=<uid of the mod the comment belongs to>, comment={"author","uid","date","text"}
    like: uid-<the uid of the mod that was liked>

Can also send a UPLOAD_MOD command directly using writeToServer
"UPLOAD_MOD","modname.zip",{mod info}, qfile

modInfo function is called when the client recieves a modvault_info command.
It should have a message dict with the following keys:
uid         - Unique identifier for a mod. Also needed ingame.
name        - Name of the mod. Also the name of the folder the mod will be located in.
description - A general description of the mod. As seen ingame
author      - The FAF username of the person that uploaded the mod.
downloads   - An integer containing the amount of downloads of this mod
likes       - An integer containing the amount of likes the mod has recieved. #TODO: Actually implement an inteface for this.
comments    - A python list containing dictionaries containing the keys as described above.
bugreports  - A python list containing dictionaries containing the keys as described above.
date        - A string describing the date the mod was uploaded. Format: "%Y-%m-%d %H:%M:%S" eg: 2012-10-28 16:50:28
ui          - A boolean describing if it is a ui mod yay or nay.
big         - A boolean describing if this mod is to be considered a big mod. Chosen by the uploader for better filtering
small       - A boolean describing if this mod is to be considered a small mod. It could be that both big and small are false.
link        - Direct link to the zip file containing the mod.
thumbnail   - A direct link to the thumbnail file. Should be something suitable for util.icon(). Not yet tested if this works correctly

Additional stuff:
fa.exe now has a CheckMods method, which is used in fa.exe.check
check has a new argument 'additional_mods' for this.
In client._clientwindow joinGameFromURL is changed. The url should have a
queryItemValue called 'mods' which with json can be translated in a list of modnames
so that it can be checked with checkMods.
handle_game_launch should have a new key in the form of mods, which is a list of modnames
to be checked with checkMods.

Stuff to be removed:
In _gameswidget.py in hostGameCLicked setActiveMods is called.
This should be done in the faf.exe.check function or in the lobby code.
It is here because the server doesn't yet send the mods info.

The tempAddMods function should be removed after the server can return mods in the modvault.
"""

import os
import zipfile

from PyQt4 import QtCore, QtGui

from modvault.utils import *
from modwidget import ModWidget
from uploadwidget import UploadModWidget
from uimodwidget import UIModWidget

import util
import logging
import time
logger = logging.getLogger("faf.modvault")
logger.setLevel(logging.DEBUG)

d = datetostr(now())
'''
tempmod1 = dict(uid=1,name='Mod1', comments=[],bugreports=[], date = d,
                ui=True, big=False,small=False, downloads=0, likes=0,
                thumbnail="",author='johnie102',
                description="""Lorem ipsum dolor sit amet, consectetur adipiscing elit. """,)
'''

FormClass, BaseClass = util.loadUiType("modvault/modvault.ui")

class ModVault(FormClass, BaseClass):
    def __init__(self, client, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)

        self.setupUi(self)
        
        self.client = client
        self.client.modsTab.layout().addWidget(self)

        logger.debug("Mod Vault tab instantiating")
        self.loaded = False

        self.modList.setItemDelegate(ModItemDelegate(self))
        self.modList.itemDoubleClicked.connect(self.modClicked)
        self.searchButton.clicked.connect(self.search)
        self.searchInput.returnPressed.connect(self.search)
        self.uploadButton.clicked.connect(self.openUploadForm)
        self.UIButton.clicked.connect(self.openUIModForm)

        self.SortType.currentIndexChanged.connect(self.sortChanged)
        self.ShowType.currentIndexChanged.connect(self.showChanged)

        self.client.showMods.connect(self.tabOpened)
        self.client.modVaultInfo.connect(self.modInfo)

        self.sortType = "alphabetical"
        self.showType = "all"
        self.searchString = ""

        self.mods = {}
        self.uids = [mod.uid for mod in getInstalledMods()]

        #tempAddMods(self)

    @QtCore.pyqtSlot(dict)
    def modInfo(self, message): #this is called when the database has send a mod to us
        """
        See above for the keys neccessary in message.
        """
        uid = message["uid"]
        if not uid in self.mods:
            mod = ModItem(self, uid)
            self.mods[uid] = mod
            self.modList.addItem(mod)
        else : 
            mod = self.mods[uid]
        mod.update(message)
        
        

    @QtCore.pyqtSlot(int)
    def sortChanged(self, index):
        if index == -1 or index == 0:
            self.sortType = "alphabetical"
        elif index == 1:
            self.sortType = "date"
        elif index == 2:
            self.sortType = "rating"
        elif index == 3:
            self.sortType = "downloads"
        self.updateVisibilities()

    @QtCore.pyqtSlot(int)
    def showChanged(self, index):
        if index == -1 or index == 0:
            self.showType = "all"
        elif index == 1:
            self.showType = "ui"
        elif index == 2:
            self.showType = "big"
        elif index == 3:
            self.showType = "small"
        elif index == 4:
            self.showType = "yours"
        self.updateVisibilities()
    

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def modClicked(self, item):
        widget = ModWidget(self, item)
        widget.exec_()

    @QtCore.pyqtSlot()
    def search(self):
        self.searchString = self.searchInput.text().lower()
        self.updateVisibilities()

    @QtCore.pyqtSlot()
    def openUIModForm(self):
        dialog = UIModWidget(self)
        dialog.exec_()
    
    @QtCore.pyqtSlot()
    def openUploadForm(self):
        modDir = QtGui.QFileDialog.getExistingDirectory(self.client, "Select the mod directory to upload", MODFOLDER,  QtGui.QFileDialog.ShowDirsOnly)
        logger.debug("Uploading mod from: " + modDir)
        if modDir != "":
            if isModFolderValid(modDir):
                #os.chmod(modDir, S_IWRITE) Don't need this at the moment
                modinfofile, modinfo = parseModInfo(modDir)
                if modinfofile.error:
                    logger.debug("There were " + str(modinfofile.errors) + " errors and " + str(modinfofile.warnings) + " warnings.")
                    logger.debug(modinfofile.errorMsg)
                    QtGui.QMessageBox.critical(self.client, "Lua parsing error", modinfofile.errorMsg + "\nMod uploading cancelled.")
                else:
                    if modinfofile.warning:
                        uploadmod = QtGui.QMessageBox.question(self.client, "Lua parsing warning", modinfofile.errorMsg + "\nDo you want to upload the mod?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                    else:
                        uploadmod = QtGui.QMessageBox.Yes
                    if uploadmod == QtGui.QMessageBox.Yes:
                        modinfo = ModInfo(**modinfo)
                        modinfo.setFolder(os.path.split(modDir)[1])
                        modinfo.update()
                        dialog = UploadModWidget(self, modDir, modinfo)
                        dialog.exec_()
            else :
                QtGui.QMessageBox.information(self.client,"Mod selection",
                        "This folder doesn't contain a mod_info.lua file")

    @QtCore.pyqtSlot()
    def tabOpened(self):
        self.client.send(dict(command="modvault",type="start"))

    def updateVisibilities(self):
        for mod in self.mods:
            self.mods[mod].updateVisibility()

    def downloadMod(self, mod):
        if downloadMod(mod):
            self.uids = [mod.uid for mod in getInstalledMods()]
            return True
        else: return False
        

#the drawing helper function for the modlist
class ModItemDelegate(QtGui.QStyledItemDelegate):
    
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
        
        #Frame around the icon
        pen = QtGui.QPen()
        pen.setWidth(1);
        pen.setBrush(QtGui.QColor("#303030"));  #FIXME: This needs to come from theme.
        pen.setCapStyle(QtCore.Qt.RoundCap);
        painter.setPen(pen)
        painter.drawRect(option.rect.left()+5-2, option.rect.top()+3, iconsize.width(), iconsize.height())

        #Description
        painter.translate(option.rect.left() + iconsize.width() + 10, option.rect.top()+4)
        clip = QtCore.QRectF(0, 0, option.rect.width()-iconsize.width() - 10 - 5, option.rect.height())
        html.drawContents(painter, clip)
  
        painter.restore()
        

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(ModItem.TEXTWIDTH)
        return QtCore.QSize(ModItem.ICONSIZE + ModItem.TEXTWIDTH + ModItem.PADDING, ModItem.ICONSIZE + ModItem.PADDING)  

class ThumbnailDownloader(QtCore.QThread):
    def __init__(self, url, moditem):
        self.url = url
        self.moditem = moditem       
        QtCore.QThread.__init__(self)

    def run(self):
        print self.url
        req = urllib2.Request(self.url, headers={'User-Agent' : "FAF Client"})
        thmb = urllib2.urlopen(req)
        print thmb
        print self.url
        fname = os.path.join(util.CACHE_DIR, os.path.split(self.url)[1])
        print fname
        with open(fname, 'wb') as fp:
            shutil.copyfileobj(thmb, fp)
            fp.flush()
            os.fsync(fp.fileno())       #probably works fine without the flush and fsync
            fp.close()
            
            #Create alpha-mapped preview image
            f = FIPY.Image(fname)
            f.setSize((100,100))
            f.save(fname)
            logger.debug("Mod Preview downloaded from %s" % self.url)

        self.moditem.thumbnail = util.icon(fname, False)
        self.moditem.setIcon(self.moditem.thumbnail)
        

class ModItem(QtGui.QListWidgetItem):
    TEXTWIDTH = 230
    ICONSIZE = 100
    PADDING = 10
    
    WIDTH = ICONSIZE + TEXTWIDTH
    #DATA_PLAYERS = 32
    
    
    FORMATTER_MOD = unicode(util.readfile("modvault/modinfo.qthtml"))
    
    def __init__(self, parent, uid, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.parent = parent
        self.uid = uid
        self.name = ""
        self.description = ""
        self.author = ""
        self.version = 0
        self.downloads = 0
        self.likes = 0
        self.comments = [] #every element is a dictionary with a 
        self.bugreports = [] #text, author and date key
        self.date = None
        self.isuidmod = False
        self.isbigmod = False
        self.issmallmod = False
        self.uploadedbyuser = False

        self.thumbnail = None
        self.link = ""
        self.loadThread = None
        self.setHidden(True)

    def update(self, dic):
        print dic
        self.name = dic["name"]
        self.description = dic["description"]
        self.version = dic["version"]
        self.author = dic["author"]
        self.downloads = dic["downloads"]
        self.likes = dic["likes"]
        self.comments = dic["comments"]
        self.bugreports = dic["bugreports"]
        self.date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(dic['date']))
        self.isuimod = dic["ui"]
        self.isbigmod = dic["big"]
        self.issmallmod = dic["small"]
        self.link = dic["link"] #Direct link to the zip file.
        self.thumbstr = dic["thumbnail"]# direct url to the thumbnail file.
        self.uploadedbyuser = (self.author == self.parent.client.login)

        self.thumbnail = None
        if self.thumbstr == "":
            self.setIcon(util.icon("games/unknown_map.png"))
        else:
            self.loadThread = ThumbnailDownloader(self.thumbstr, self)
            self.loadThread.run()

        if len(self.description) < 200:
            descr = self.description
        else:
            descr = self.description[:197] + "..."

        modtype = ""
        if self.isuimod: modtype ="UI mod"
        elif self.isbigmod: modtype="big mod"
        elif self.issmallmod: modtype="small mod"
        if self.uid in self.parent.uids: color="green"
        else: color="white"
        self.setText(self.FORMATTER_MOD.format(color=color,version=str(self.version),title=self.name,
            description=descr, author=self.author,downloads=str(self.downloads),
            likes=str(self.likes),date=str(self.date),modtype=modtype))

        self.setToolTip('<p width="230">%s</p>' % self.description)
        self.updateVisibility()

    def shouldBeVisible(self):
        p = self.parent
        if p.searchString != "":
            if not (self.author.lower().find(p.searchString) != -1 or  self.name.lower().find(p.searchString) != -1):
                return False
        if p.showType == "all":
            return True
        elif p.showType == "ui":
            return self.isuimod
        elif p.showType == "big":
            return self.isbigmod
        elif p.showType == "small":
            return self.issmallmod
        elif p.showType == "yours":
            return self.uploadedbyuser
        else: #shouldn't happen
            return True

    def updateVisibility(self):
        self.setHidden(not self.shouldBeVisible())

    def __ge__(self, other):
        return not self.__lt__(self, other)

    def __lt__(self, other):
        if self.parent.sortType == "alphabetical":
            if self.name.lower() == other.name.lower():
                return (self.uid < other.uid)
            return (self.name.lower() > other.name.lower())
        elif self.parent.sortType == "rating":
            if self.rating == other.rating:
                return (self.downloads < other.downloads)
            return (self.rating < other.rating)
        elif self.parent.sortType == "downloads":
            if self.downloads == other.downloads:
                return (self.date < other.date)
            return (self.downloads < other.downloads)
        elif self.parent.sortType == "date":
            if self.date == other.date:
                return (self.name.lower() < other.name.lower())
            return (self.date < other.date)

