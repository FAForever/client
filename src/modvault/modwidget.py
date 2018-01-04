from PyQt5 import QtCore, QtWidgets
import util

FormClass, BaseClass = util.THEME.loadUiType("modvault/mod.ui")


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
        modtext = "UI mod\n" if mod.is_uimod else ""
        self.Info.setText("{}By {}\nUploaded {}".format(modtext, mod.author, mod.date))
        if mod.thumbnail is None:
            self.Picture.setPixmap(util.THEME.pixmap("games/unknown_map.png"))
        elif not isinstance(mod.thumbnail, str):
            self.Picture.setPixmap(mod.thumbnail.pixmap(100, 100))

        self.tabWidget.setEnabled(False)

        if self.mod.uid in self.parent.uids:
            self.DownloadButton.setText("Remove Mod")
        self.DownloadButton.clicked.connect(self.download)

        self.likeButton.setEnabled(False)
        self.LineComment.setEnabled(False)
        self.LineBugReport.setEnabled(False)

    @QtCore.pyqtSlot()
    def download(self):
        if self.mod.uid not in self.parent.uids:
            self.parent.download_mod(self.mod)
            self.done(1)
        else:
            show = QtWidgets.QMessageBox.question(self.parent.client, "Delete Mod",
                                                  "Are you sure you want to delete this mod?",
                                                  QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
            if show == QtWidgets.QMessageBox.Yes:
                self.parent.remove_mod(self.mod)
                self.done(1)
