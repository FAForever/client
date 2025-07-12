import json
import logging
import os
import sys
from typing import Any
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
        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.on_releases_received)

    @property
    def adapter_kind(self) -> str:
        return Settings.get("iceadapter/kind", "java")

    @property
    def forced_version(self) -> str:
        return Settings.get(f"iceadapter/{self.adapter_kind}_version", "")

    @property
    def latest_version(self) -> str:
        return Settings.get(f"iceadapter/{self.adapter_kind}_latest", "")

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

        if self.forced_version:
            for release in releases:
                if (
                    release["tag_name"] == self.forced_version
                    and self.download_if_necessary(release["assets"])
                ):
                    self.done.emit()
                    return

        for release in releases:
            if self.download_if_necessary(release["assets"]):
                if self.latest_version != release["tag_name"]:
                    Settings.set(f"iceadapter/{self.adapter_kind}_latest", release["tag_name"])
                    self.latest_version = release["tag_name"]
                self.done.emit()
                return

    def download_if_necessary(self, assets: list[dict[str, Any]]) -> bool:
        for asset in assets:
            if self.platform_name() in asset["name"]:
                url = asset["browser_download_url"]
                filename = os.path.basename(url)
                if not os.path.exists(os.path.join(ICE_ADAPTER_DIR, filename)):
                    return download_file(url, ICE_ADAPTER_DIR, filename, "Tool", silent=False)
                return True
        else:
            return False
