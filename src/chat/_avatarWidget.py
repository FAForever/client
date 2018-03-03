from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest

import util


class AvatarWidget(QtWidgets.QDialog):
    def __init__(self, parent, user, *args, **kwargs):

        QtWidgets.QDialog.__init__(self, *args, **kwargs)

        self.user = user
        self.parent = parent

        self.setStyleSheet(self.parent.styleSheet())
        self.setWindowTitle("Avatar manager")

        self.groupLayout = QtWidgets.QVBoxLayout(self)
        self.avatarList = QtWidgets.QListWidget()

        self.avatarList.setWrapping(1)
        self.avatarList.setSpacing(5)
        self.avatarList.setResizeMode(1)

        self.groupLayout.addWidget(self.avatarList)

        self.item = []
        self.parent.lobby_info.avatarList.connect(self.avatar_list)

        self.nams = {}
        self.avatars = {}

        self.finished.connect(self.cleaning)

    def showEvent(self, event):
        self.parent.requestAvatars()

    def finish_request(self, reply):
        if reply.url().toString() in self.avatars:
            img = QtGui.QImage()
            img.loadFromData(reply.readAll())
            pix = QtGui.QPixmap(img)
            self.avatars[reply.url().toString()].setIcon(QtGui.QIcon(pix))
            self.avatars[reply.url().toString()].setIconSize(pix.rect().size())
            util.addrespix(reply.url().toString(), QtGui.QPixmap(img))

    def clicked(self):
        self.doit(None)
        self.close()

    def create_connect(self, x):
        return lambda: self.doit(x)

    def doit(self, val):
        self.parent.lobby_connection.send(dict(command="avatar", action="select", avatar=val))
        self.close()

    def avatar_list(self, avatar_list):
        self.avatarList.clear()
        button = QtWidgets.QPushButton()
        self.avatars["None"] = button
        button.clicked.connect(self.clicked)

        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(QtCore.QSize(40, 20))
        self.item.append(item)

        self.avatarList.addItem(item)
        self.avatarList.setItemWidget(item, button)

        for avatar in avatar_list:
            avatarPix = util.respix(avatar["url"])
            button = QtWidgets.QPushButton()
            button.clicked.connect(self.create_connect(avatar["url"]))

            item = QtWidgets.QListWidgetItem()
            item.setSizeHint(QtCore.QSize(40, 20))
            self.item.append(item)
            self.avatarList.addItem(item)

            button.setToolTip(avatar["tooltip"])
            url = QtCore.QUrl(avatar["url"])
            self.avatars[avatar["url"]] = button

            self.avatarList.setItemWidget(item, self.avatars[avatar["url"]])

            if not avatarPix:
                self.nams[url] = QNetworkAccessManager(button)
                self.nams[url].finished.connect(self.finish_request)
                self.nams[url].get(QNetworkRequest(url))
            else:
                self.avatars[avatar["url"]].setIcon(QtGui.QIcon(avatarPix))
                self.avatars[avatar["url"]].setIconSize(avatarPix.rect().size())

    def cleaning(self):
        self.parent.lobby_info.avatarList.disconnect(self.avatar_list)
