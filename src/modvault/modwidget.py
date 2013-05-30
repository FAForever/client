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

from PyQt4 import QtCore, QtGui

import modvault
from modvault import datetostr,strtodate,now


FormClass, BaseClass = util.loadUiType("modvault/mod.ui")


class ModWidget(FormClass, BaseClass):
    def __init__(self, parent, mod, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)       

        self.setupUi(self)
        self.parent = parent
        
        
        self.setStyleSheet(self.parent.client.styleSheet())
        
        self.setWindowTitle(mod.name)
        self.Title.setText(mod.name)
        self.Description.setText(mod.description)
        self.Info.setText("By %s. Uploaded %s. Last updated %s" % (mod.author,
                                    str(mod.date), str(mod.last_updated)))
        if mod.thumbnail == None:
            self.Picture.setPixmap(util.icon("games/unknown_map.png"))
        else:
            self.Picture.setPixmap(mod.thumbnail)

        self.Comments.setItemDelegate(CommentItemDelegate(self))
        self.BugReports.setItemDelegate(CommentsItemDelegate(self))
        
        self.DownloadButton.clicked.connect(self.download)
        self.LineComment.returnPressed.connect(self.addComment)
        self.LineBugReport.returnPressed.connect(self.addBugReport)

        for item in mod.comments:
            comment = CommentItem(self,item["uid"])
            comment.update(item)
            self.Comments.addItem(comment)
        for item in mod.bugReports:
            comment = CommentItem(self,item["uid"])
            comment.update(item)
            self.BugReports.addItem(comment)

        self.mod = mod
        
    @QtCore.pyqtSlot()
    def download(self):
        link = urllib2.unquote(mod.link)
        if not mod.name in self.parent.installedMods:
            self.parent.downloadMod(mod)
        else:
            show = QtGui.QMessageBox.question(self.client, "Already got the Mod", "Seems like you already have that mod!<br/><b>Would you like to see it?</b>", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
            if show == QtGui.QMessageBox.Yes:
                util.showInExplorer(modvault.modToFilename(mod))

    @QtCore.pyqtSlot()
    def addComment(self):
        comment = {"author":self.parent.client.login, "text":self.LineComment.text(),
                   "date":datetostr(now()), "uid":"%d00%d" % (self.mod.uid, len(self.mod.bugReports)+len(self.mod.comments)))}
        
        self.parent.client.send(dict(command="modvault",type="addcomment",comment=comment))
        c = CommentItem(self, comment["uid"])
        c.update(comment)
        self.Comments.addItem(c)
        self.mod.comments.append(comment)

    @QtCore.pyqtSlot()
    def addBugReport(self):
        bugreport = {"author":self.parent.client.login, "text":self.LineComment.text(),
                   "date":datetostr(now()), "uid":int("%d00%d" % (self.mod.uid, len(self.mod.bugReports) + +len(self.mod.comments)))}
        
        self.parent.client.send(dict(command="modvault",type="addbugreport",bugreport=bugreport))
        c = CommentItem(self, bugreport["uid"])
        c.update(bugreport)
        self.BugReports.addItem(c)
        self.mod.bugReports.append(bugreport)

class CommentItemDelegate(QtGui.QStyledItemDelegate):
    TEXTWIDTH = 350
    TEXTHEIGHT = 50
    def __init__(self, *args, **kwargs):
        QtGui.QStyledItemDelegate.__init__(self, *args, **kwargs)
        
    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
                
        painter.save()
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
                
        option.text = ""  
        option.widget.style().drawControl(QtGui.QStyle.CE_ItemViewItem, option, painter, option.widget)
        

        #Description
        painter.translate(option.rect.left() + iconsize.width() + 10, option.rect.top()+10)
        clip = QtCore.QRectF(0, 0, option.rect.width(), option.rect.height())
        html.drawContents(painter, clip)
  
        painter.restore()
        

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(self.TEXTWIDTH)
        return QtCore.QSize(self.TEXTWIDTH, self.TEXTHEIGHT)  

class CommentItem(QtGui.QListWidgetItem):
    FORMATTER_COMMENT = unicode(util.readfile("modvault/comment.qthtml"))
    def __init__(self, parent, uid, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.parent = parent
        self.uid = uid
        self.text = ""
        self.author = ""
        self.date = None

    def update(self, dic):
        self.text = dic["text"]
        self.author = dic["author"]
        self.date = strtodate(dic["date"])
        self.setText(self.FORMATTER_COMMENT.format(text=self.text,author=self.author,date=str(self.date)))

    def __ge__(self, other):
        return self.date > other.date

    def __lt__(self, other):
        return self.date <= other.date
