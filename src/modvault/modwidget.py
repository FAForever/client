

import urllib.request, urllib.error, urllib.parse

from PyQt5 import QtCore, QtWidgets

from util import strtodate, datetostr, now
import util

FormClass, BaseClass = util.loadUiType("modvault/mod.ui")


class ModWidget(FormClass, BaseClass):
    def __init__(self, parent, mod, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)
        self.parent = parent
        
        self.setStyleSheet(self.parent.client.styleSheet())
        
        self.setWindowTitle(mod.name)

        self.mod = mod
        
        self.Title.setText(mod.name)
        self.Description.setText(mod.description)
        modtext = ""
        if mod.isuimod: modtext = "UI mod\n"
        self.Info.setText(modtext + "By %s\nUploaded %s" % (mod.author,
                                    str(mod.date)))
        if mod.thumbnail == None:
            self.Picture.setPixmap(util.pixmap("games/unknown_map.png"))
        else:
            self.Picture.setPixmap(mod.thumbnail.pixmap(100,100))

        #self.Comments.setItemDelegate(CommentItemDelegate(self))
        #self.BugReports.setItemDelegate(CommentItemDelegate(self))

        self.tabWidget.setEnabled(False)

        if self.mod.uid in self.parent.uids:
            self.DownloadButton.setText("Remove Mod")
        self.DownloadButton.clicked.connect(self.download)

        #self.likeButton.clicked.connect(self.like)
        #self.LineComment.returnPressed.connect(self.addComment)
        #self.LineBugReport.returnPressed.connect(self.addBugReport)

        #for item in mod.comments:
        #    comment = CommentItem(self,item["uid"])
        #    comment.update(item)
        #    self.Comments.addItem(comment)
        #for item in mod.bugreports:
        #    comment = CommentItem(self,item["uid"])
        #    comment.update(item)
        #    self.BugReports.addItem(comment)

        self.likeButton.setEnabled(False)
        self.LineComment.setEnabled(False)
        self.LineBugReport.setEnabled(False)

        
    @QtCore.pyqtSlot()
    def download(self):
        if not self.mod.uid in self.parent.uids:
            self.parent.downloadMod(self.mod)
            self.done(1)
        else:
            show = QtWidgets.QMessageBox.question(self.parent.client, "Delete Mod", "Are you sure you want to delete this mod?", QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
            if show == QtWidgets.QMessageBox.Yes:
                self.parent.removeMod(self.mod)
                self.done(1)

    @QtCore.pyqtSlot()
    def addComment(self):
        if self.LineComment.text() == "": return
        comment = {"author":self.parent.client.login, "text":self.LineComment.text(),
                   "date":datetostr(now()), "uid":"%s-%s" % (self.mod.uid, str(len(self.mod.bugreports)+len(self.mod.comments)).zfill(3))}
        
        self.parent.client.lobby_connection.send(dict(command="modvault",type="addcomment",moduid=self.mod.uid,comment=comment))
        c = CommentItem(self, comment["uid"])
        c.update(comment)
        self.Comments.addItem(c)
        self.mod.comments.append(comment)
        self.LineComment.setText("")

    @QtCore.pyqtSlot()
    def addBugReport(self):
        if self.LineBugReport.text() == "": return
        bugreport = {"author":self.parent.client.login, "text":self.LineBugReport.text(),
                   "date":datetostr(now()), "uid":"%s-%s" % (self.mod.uid, str(len(self.mod.bugreports) + +len(self.mod.comments)).zfill(3))}
        
        self.parent.client.lobby_connection.send(dict(command="modvault",type="addbugreport",moduid=self.mod.uid,bugreport=bugreport))
        c = CommentItem(self, bugreport["uid"])
        c.update(bugreport)
        self.BugReports.addItem(c)
        self.mod.bugreports.append(bugreport)
        self.LineBugReport.setText("")

    @QtCore.pyqtSlot()
    def like(self): #the server should determine if the user hasn't already clicked the like button for this mod.
        self.parent.client.lobby_connection.send(dict(command="modvault",type="like", uid=self.mod.uid))
        self.likeButton.setEnabled(False)

class CommentItemDelegate(QtWidgets.QStyledItemDelegate):
    TEXTWIDTH = 350
    TEXTHEIGHT = 60
    def __init__(self, *args, **kwargs):
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)
        
    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
                
        painter.save()
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
                
        option.text = ""  
        option.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter, option.widget)
        

        #Description
        painter.translate(option.rect.left() + 10, option.rect.top()+10)
        clip = QtCore.QRectF(0, 0, option.rect.width(), option.rect.height())
        html.drawContents(painter, clip)
  
        painter.restore()
        

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(self.TEXTWIDTH)
        return QtCore.QSize(self.TEXTWIDTH, self.TEXTHEIGHT)

class CommentItem(QtWidgets.QListWidgetItem):
    FORMATTER_COMMENT = str(util.readfile("modvault/comment.qthtml"))
    def __init__(self, parent, uid, *args, **kwargs):
        QtWidgets.QListWidgetItem.__init__(self, *args, **kwargs)

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
