from __future__ import annotations

from PyQt6.QtGui import QIcon
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QListWidget
from PyQt6.QtWidgets import QListWidgetItem

from src import util
from src.api.models.Avatar import Avatar
from src.api.models.AvatarAssignment import AvatarAssignment
from src.downloadManager import CachedImageDownloader
from src.downloadManager import DownloadRequest


class AvatarHandler:
    def __init__(self, avatar_list: QListWidget, avatar_downloader: CachedImageDownloader) -> None:
        self.avatar_list = avatar_list
        self.avatar_list.setVerticalScrollMode(self.avatar_list.ScrollMode.ScrollPerPixel)
        self.avatar_dler = avatar_downloader
        self.requests = {}

    def populate_avatars(self, avatar_assignments: list[AvatarAssignment] | None) -> None:
        if avatar_assignments is None:
            return

        for assignment in avatar_assignments:
            if self.avatar_dler.has_image(assignment.avatar.filename):
                self._add_avatar(assignment.avatar)
            else:
                self._download_avatar(assignment.avatar)

    def _prepare_avatar_dl_request(self, avatar: Avatar) -> DownloadRequest:
        req = DownloadRequest()
        req.done.connect(self._handle_avatar_download)
        self.requests[avatar.url] = (req, avatar.tooltip)
        return req

    def _download_avatar(self, avatar: Avatar) -> None:
        req = self._prepare_avatar_dl_request(avatar)
        self.avatar_dler.download_image(avatar.url, req)

    def _add_avatar(self, avatar: Avatar) -> None:
        self._add_avatar_item(self.avatar_dler.get_image(avatar.filename), avatar.tooltip)

    def _add_avatar_item(self, pixmap: QPixmap, description: str) -> None:
        if pixmap.isNull():
            icon = QIcon(util.THEME.pixmap("chat/avatar/avatar_blank.png").scaled(40, 20))
        else:
            icon = QIcon(pixmap.scaled(40, 20))
        avatar_item = QListWidgetItem(icon, description)
        self.avatar_list.addItem(avatar_item)

    def _handle_avatar_download(self, url: str, pixmap: QPixmap) -> None:
        _, tooltip = self.requests[url]
        self._add_avatar_item(pixmap, tooltip)
        del self.requests[url]
