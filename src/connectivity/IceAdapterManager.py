import json
import logging
import os
import sys
from typing import ClassVar
from typing import NamedTuple
from typing import Protocol

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


class IceAdapterPlatformOptions(Protocol):
    def name(self) -> str: ...
    def extension(self) -> str: ...


class GoIceAdapterPlatformOptions(NamedTuple):
    windows: str = "windows-amd64"
    linux: str = "linux-amd64"

    def name(self) -> str:
        if sys.platform == "win32":
            return self.windows
        return self.linux

    def extension(self) -> str:
        return ".exe" if sys.platform == "win32" else ""


class JavaIceAdapterPlatformOptions(NamedTuple):
    windows: str = "win"
    linux: str = "linux"

    def name(self) -> str:
        if sys.platform == "win32":
            return self.windows
        return self.linux

    def extension(self) -> str:
        return ".jar"


@with_logger
class IceAdapterManager(QObject):
    _logger: ClassVar[logging.Logger]

    done = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.adapter_kind = Settings.get("iceadapter/kind", "java")
        self.current_version = Settings.get(f"iceadapter/{self.adapter_kind}_version", "")
        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.on_releases_received)

    def get_releases(self) -> None:
        if self.adapter_kind == "java":
            url_str = Settings.get("JAVA_ICE_ADAPTER_RELEASE_URL", "")
        else:
            url_str = Settings.get("GO_ICE_ADAPTER_RELEASE_URL", "")
        req = QNetworkRequest(QUrl(url_str))
        self.nam.get(req)

    def platform_name(self) -> str:
        if self.adapter_kind == "java":
            return JavaIceAdapterPlatformOptions().name()
        else:
            return GoIceAdapterPlatformOptions().name()

    def on_releases_received(self, reply: QNetworkReply) -> None:
        if reply.error() != reply.NetworkError.NoError:
            self._logger.error(
                "Could not get ICE adapter releases from GitHub API (%s): %s",
                reply.url().url(),
                reply.errorString(),
            )
            return
        releases = json.loads(reply.readAll().data())
        # check first 5 releases. why 5? just cause
        # there is a possibility that releaser will mess up
        # and create release manually, which will result
        # in missing assets
        for release in releases[:5]:
            for asset in release["assets"]:
                if self.platform_name() in asset["name"]:
                    url = asset["browser_download_url"]
                    filename = os.path.basename(url)
                    if not os.path.exists(os.path.join(ICE_ADAPTER_DIR, filename)):
                        download_file(url, ICE_ADAPTER_DIR, filename, "Tool", silent=False)

                    if self.current_version != release["tag_name"]:
                        Settings.set(f"iceadapter/{self.adapter_kind}_version", release["tag_name"])
                        self.current_version = release["tag_name"]
                    self.done.emit()
                    return
