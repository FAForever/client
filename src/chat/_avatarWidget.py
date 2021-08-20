from PyQt5.QtCore import QObject, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QListWidgetItem, QPushButton

from downloadManager import DownloadRequest


class AvatarWidget(QObject):
    def __init__(
        self, parent_widget, lobby_connection, lobby_info, avatar_dler, theme,
    ):
        QObject.__init__(self, parent_widget)

        self._parent_widget = parent_widget
        self._lobby_connection = lobby_connection
        self._lobby_info = lobby_info
        self._avatar_dler = avatar_dler

        self.items = {}
        self.requests = {}
        self.buttons = {}

        self.set_theme(theme)

        self._lobby_info.avatarList.connect(self.set_avatar_list)
        self.base.finished.connect(self.clean)

    @classmethod
    def builder(
        cls, parent_widget, lobby_connection, lobby_info, avatar_dler,
        theme, **kwargs
    ):
        return lambda: cls(
            parent_widget, lobby_connection, lobby_info, avatar_dler, theme,
        )

    def set_theme(self, theme):
        formc, basec = theme.loadUiType("dialogs/avatar.ui")
        self.form = formc()
        self.base = basec(self._parent_widget)
        self.form.setupUi(self.base)

    @property
    def avatar_list(self):
        return self.form.avatarList

    def show(self):
        self._lobby_connection.send({
            "command": "avatar",
            "action": "list_avatar",
        })
        self.base.show()

    def select_avatar(self, val):
        self._lobby_connection.send({
            "command": "avatar",
            "action": "select",
            "avatar": val,
        })
        self.base.close()

    def set_avatar_list(self, avatars):
        self.avatar_list.clear()

        self._add_avatar_item(None)
        for avatar in avatars:
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

        self.avatar_list.addItem(item)
        self.avatar_list.setItemWidget(item, button)

    def _set_avatar_icon(self, val, icon):
        button = self.buttons[val]
        button.setIcon(QIcon(icon))
        button.setIconSize(icon.rect().size())

    def _handle_avatar_download(self, url, icon):
        del self.requests[url]
        self._set_avatar_icon(url, icon)

    def clean(self):
        self.setParent(None)    # let ourselves get GC'd
