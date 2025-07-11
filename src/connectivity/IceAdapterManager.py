import json
import logging
import os
import sys
from typing import ClassVar
from typing import NamedTuple

from PyQt6.QtCore import QObject
from PyQt6.QtCore import QUrl
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtNetwork import QNetworkRequest

from src.config import Settings
from src.decorators import with_logger
from src.util import ICE_ADAPTER_DIR
from src.vaults.dialogs import download_file


class IceAdapterPlatformOptions(NamedTuple):
    windows: str = "windows-amd64"
    linux: str = "linux-amd64"

    def name(self) -> str:
        if sys.platform == "win32":
            return self.windows
        return self.linux

    def extension(self) -> str:
        return ".exe" if sys.platform == "win32" else ""


@with_logger
class IceAdapterManager(QObject):
    _logger: ClassVar[logging.Logger]

    done = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.on_releases_received)

    def get_releases(self) -> None:
        req = QNetworkRequest(QUrl(Settings.get("ICE_ADAPTER_RELEASE_URL", "")))
        self.nam.get(req)

    def on_releases_received(self, reply: QNetworkReply) -> None:
        if reply.error() != reply.NetworkError.NoError:
            self._logger.error(
                "Could not get ICE adapter releases from GitHub API (%s): %s",
                reply.url().url(),
                reply.errorString(),
            )
            return
        releases = json.loads(reply.readAll().data())
        for asset in releases[0]["assets"]:
            if IceAdapterPlatformOptions().name() in asset["name"]:
                url = asset["browser_download_url"]
                filename = os.path.basename(url)
                if not os.path.exists(os.path.join(ICE_ADAPTER_DIR, filename)):
                    download_file(url, ICE_ADAPTER_DIR, os.path.basename(url), "Tool", silent=False)
                break
        self.done.emit(releases[0]["tag_name"])
