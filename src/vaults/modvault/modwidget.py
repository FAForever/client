
import os
import urllib.parse

from PyQt5 import QtCore, QtGui, QtWidgets

import util
from util import strtodate

from .modvault import utils

FormClass, BaseClass = util.THEME.loadUiType("vaults/modvault/mod.ui")


class ModWidget(FormClass, BaseClass):
    ICONSIZE = QtCore.QSize(100, 100)

    def __init__(self, parent, mod, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)
        self.parent = parent

        util.THEME.stylesheets_reloaded.connect(self.load_stylesheet)
        self.load_stylesheet()

        self.setWindowTitle(mod.name)

        self.mod = mod

        self.Title.setText(mod.name)
        self.Description.setText(mod.description)
        modtext = ""
        if mod.isuimod:
            modtext = "UI mod\n"
        self.Info.setText(
            modtext + "By {}\nUploaded {}".format(mod.author, str(mod.date)),
        )
        mod.thumbnail = utils.getIcon(
            os.path.basename(urllib.parse.unquote(mod.thumbstr)),
        )
        if mod.thumbnail is None:
            self.Picture.setPixmap(util.THEME.pixmap("games/unknown_map.png"))
        else:
            pixmap = util.THEME.pixmap(mod.thumbnail, False)
            self.Picture.setPixmap(pixmap.scaled(self.ICONSIZE))

        # ensure that pixmap is set
        if self.Picture.pixmap() is None or self.Picture.pixmap().isNull():
            self.Picture.setPixmap(util.THEME.pixmap("games/unknown_map.png"))

        # self.Comments.setItemDelegate(CommentItemDelegate(self))
        # self.BugReports.setItemDelegate(CommentItemDelegate(self))

        self.tabWidget.setEnabled(False)

        if self.mod.uid in self.parent.uids:
            self.DownloadButton.setText("Remove Mod")
        self.DownloadButton.clicked.connect(self.download)

        # self.likeButton.clicked.connect(self.like)
        # self.LineComment.returnPressed.connect(self.addComment)
        # self.LineBugReport.returnPressed.connect(self.addBugReport)

        # for item in mod.comments:
        #     comment = CommentItem(self,item["uid"])
        #     comment.update(item)
        #     self.Comments.addItem(comment)
        # for item in mod.bugreports:
        #     comment = CommentItem(self,item["uid"])
        #     comment.update(item)
        #     self.BugReports.addItem(comment)

        self.likeButton.setEnabled(False)
        self.LineComment.setEnabled(False)
        self.LineBugReport.setEnabled(False)

    def load_stylesheet(self):
        self.setStyleSheet(util.THEME.readstylesheet("client/client.css"))

    @QtCore.pyqtSlot()
    def download(self):
        if self.mod.uid not in self.parent.uids:
            self.parent.downloadMod(self.mod)
            self.done(1)
        else:
            show = QtWidgets.QMessageBox.question(
                self.parent.client,
                "Delete Mod",
                "Are you sure you want to delete this mod?",
                QtWidgets.QMessageBox.Yes,
                QtWidgets.QMessageBox.No,
            )
            if show == QtWidgets.QMessageBox.Yes:
                self.parent.removeMod(self.mod)
                self.done(1)

    @QtCore.pyqtSlot()
    def addComment(self):
        # TODO: implement this with the use of API
        ...

    @QtCore.pyqtSlot()
    def addBugReport(self):
        # TODO: implement this with the use of API (if possible)
        ...

    @QtCore.pyqtSlot()
    def like(self):
        # TODO: implement this with the use of API
        ...


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
        option.widget.style().drawControl(
            QtWidgets.QStyle.CE_ItemViewItem, option, painter, option.widget,
        )

        # Description
        painter.translate(option.rect.left() + 10, option.rect.top() + 10)
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
    FORMATTER_COMMENT = str(
        util.THEME.readfile("vaults/modvault/comment.qthtml"),
    )

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
        self.setText(
            self.FORMATTER_COMMENT.format(
                text=self.text,
                author=self.author,
                date=str(self.date),
            ),
        )

    def __ge__(self, other):
        return self.date > other.date

    def __lt__(self, other):
        return self.date <= other.date
