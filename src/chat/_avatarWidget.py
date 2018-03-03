from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, \
        QListWidgetItem
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from downloadManager import DownloadRequest


class AvatarWidget(QDialog):
    def __init__(self, parent_widget, lobby_connection, lobby_info,
                 avatar_dler):
        QDialog.__init__(self, parent_widget)

        self._parent_widget = parent_widget
        self._lobby_connection = lobby_connection
        self._lobby_info = lobby_info
        self._avatar_dler = avatar_dler

        self.items = {}
        self.requests = {}
        self.buttons = {}

        self.setStyleSheet(self._parent_widget.styleSheet())
        self.setWindowTitle("Avatar manager")
        self.groupLayout = QVBoxLayout(self)
        self.avatarList = QListWidget()
        self.avatarList.setWrapping(1)
        self.avatarList.setSpacing(5)
        self.avatarList.setResizeMode(1)
        self.groupLayout.addWidget(self.avatarList)

        self._lobby_info.avatarList.connect(self.avatar_list)
        self.finished.connect(self.clean)

    @classmethod
    def builder(cls, parent_widget, lobby_connection, lobby_info, avatar_dler,
                **kwargs):
        return lambda: cls(parent_widget, lobby_connection, lobby_info,
                           avatar_dler)

    def showEvent(self, event):
        self._lobby_connection.send({
            "command": "avatar",
            "action": "list_avatar"
        })

    def select_avatar(self, val):
        self._lobby_connection.send({
            "command": "avatar",
            "action": "select",
            "avatar": val
        })
        self.close()

    def avatar_list(self, avatar_list):
        self.avatarList.clear()

        self._add_avatar_item(None)
        for avatar in avatar_list:
            self._add_avatar_item(avatar)
            url = avatar["url"]
            icon = self._avatar_dler.avatars.get(url, None)
            if icon is not None:
                self._set_avatar_icon(url, icon)
            else:
                req = DownloadRequest()
                req.done.connect(self._handle_avatar_download)
                self.requests[url] = req
                self._avatar_dler.download_avatar(url, req)

    def _add_avatar_item(self, avatar):
        val = None if avatar is None else avatar["url"]
        button = QPushButton()
        button.clicked.connect(lambda: self.select_avatar(val))
        self.buttons[val] = button
        if avatar is not None:
            button.setToolTip(avatar["tooltip"])

        item = QListWidgetItem()
        item.setSizeHint(QSize(40, 20))
        self.items[val] = item

        self.avatarList.addItem(item)
        self.avatarList.setItemWidget(item, button)

    def _set_avatar_icon(self, val, icon):
        button = self.buttons[val]
        button.setIcon(QIcon(icon))
        button.setIconSize(icon.rect().size())

    def _handle_avatar_download(self, url, icon):
        del self.requests[url]
        self._set_avatar_icon(url, icon)

    def clean(self):
        self.setParent(None)    # let ourselves get GC'd
