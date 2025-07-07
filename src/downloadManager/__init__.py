from __future__ import annotations

import logging
import os
import zipfile
from io import BytesIO

from PyQt6.QtCore import QByteArray
from PyQt6.QtCore import QEventLoop
from PyQt6.QtCore import QFile
from PyQt6.QtCore import QIODevice
from PyQt6.QtCore import QObject
from PyQt6.QtCore import QSize
from PyQt6.QtCore import QTimer
from PyQt6.QtCore import QUrl
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtNetwork import QNetworkRequest

from src.config import Settings
from src.util import AVATARS_CACHE_DIR
from src.util import MAP_PREVIEW_LARGE_DIR
from src.util import MAP_PREVIEW_SMALL_DIR

logger = logging.getLogger(__name__)


class BaseDownload(QObject):
    """
    A simple async one-shot file downloader.
    """
    start = pyqtSignal(object)
    progress = pyqtSignal(object)
    finished = pyqtSignal(object)

    def __init__(
            self,
            nam: QNetworkAccessManager,
            addr: str,
            dest: QFile | BytesIO,
            destpath: str | None = None,
            request_params: dict[str, str] | None = None,
    ) -> None:
        QObject.__init__(self)
        self._nam = nam
        self.addr = addr
        self.dest = dest
        self.destpath = destpath
        self.request_params = request_params or {}

        self.canceled = False
        self.error = False

        self.blocksize: int | None = 8192
        self.bytes_total = 0
        self.bytes_progress = 0

        self._dfile: QNetworkReply | None = None

        self._reading = False
        self._running = False
        self._sock_finished = False

    def _stop(self):
        ran = self._running
        self._running = False
        if ran:
            self._about_to_finish()
            self._finish()

    def _error(self):
        self.error = True
        self._stop()

    def cancel(self):
        self.canceled = True
        if not self._dfile.isFinished():
            self._dfile.abort()
        self._stop()

    def _handle_status(self) -> None:
        # check status code
        statusCode = self._dfile.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if statusCode != 200:
            logger.debug("Download failed: %s -> %s", self.addr, statusCode)
            self.error = True

    def _about_to_finish(self) -> None:
        self._handle_status()

    def _finish(self) -> None:
        self.finished.emit(self)

    def prepare_request(self) -> QNetworkRequest:
        qurl = QUrl(self.addr)
        # in https://github.com/FAForever/faf-java-api/pull/637
        # hmac verification was introduced
        req = QNetworkRequest(qurl)
        for key, value in self.request_params.items():
            req.setRawHeader(key.encode(), value.encode())
        req.setRawHeader(b'User-Agent', b"FAF Client")
        req.setMaximumRedirectsAllowed(3)
        return req

    def run(self):
        self._running = True
        self.start.emit(self)

        self._dfile = self._nam.get(self.prepare_request())
        self._dfile.errorOccurred.connect(self._error)
        self._dfile.finished.connect(self._atFinished)
        self._dfile.downloadProgress.connect(self._atProgress)
        self._dfile.readyRead.connect(self._kick_read)
        self._kick_read()

    def _atFinished(self):
        self._sock_finished = True
        self._kick_read()

    def _atProgress(self, recv: int, total: int) -> None:
        self.bytes_progress = recv
        self.bytes_total = total
        self.progress.emit(self)

    def _kick_read(self):    # Don't run the read loop more than once at a time
        if self._reading:
            return
        self._reading = True
        self._read()
        self._reading = False

    def _read(self):
        while self._dfile.bytesAvailable() > 0 and self._running:
            self._readloop()
        if self._sock_finished:
            # Sock can be marked as finished either before read or inside
            # readloop. Either way we've read everything after it was marked
            self._stop()

    def _readloop(self):
        if self.blocksize is None:
            bs = self._dfile.bytesAvailable()
        else:
            bs = self.blocksize
        self.dest.write(self._dfile.read(bs))

    def succeeded(self):
        return not self.error and not self.canceled

    def failed(self) -> bool:
        return not self.succeeded()

    def error_string(self) -> str:
        if self._dfile is not None:
            return self._dfile.errorString()
        return ""

    def waitForCompletion(self) -> None:
        if not self._running:
            return

        wait_flag = QEventLoop.ProcessEventsFlag.WaitForMoreEvents
        loop = QEventLoop()
        self.finished.connect(loop.quit)
        loop.exec(wait_flag)


class FileDownload(BaseDownload):
    def __init__(
            self,
            target_path: str,
            nam: QNetworkAccessManager,
            addr: str,
            request_params: dict[str, str] | None = None,
    ) -> None:
        self._target_path = target_path
        self._cache_path = f"{target_path}.part"

        self._output = QFile(self._cache_path)
        self._output.open(QIODevice.OpenModeFlag.WriteOnly)
        super().__init__(nam, addr, self._output, request_params=request_params)

    def _about_to_finish(self) -> None:
        super()._about_to_finish()
        self.cleanup()

    def cleanup(self) -> None:
        self._output.close()
        if self.failed():
            try:
                os.unlink(self._cache_path)
            except OSError as e:
                logger.warning("Couldn't remove %s: %s", self._cache_path, e)
        else:
            logger.debug("Finished download from %s", self.addr)
            self._output.rename(self._target_path)


class ZipDownloadExtract(BaseDownload):
    """
    Download a zip archive in-memory and extract it into target_dir
    """

    def __init__(
            self,
            target_dir: str,
            nam: QNetworkAccessManager,
            addr: str,
            request_params: dict | None = None,
            exist_ok: bool = False,
    ) -> None:
        self._target_dir = target_dir
        self._output = BytesIO()
        self._exist_ok = exist_ok
        super().__init__(nam, addr, self._output, request_params=request_params)

    def _about_to_finish(self) -> None:
        super()._about_to_finish()
        if self.succeeded():
            self.extract_archive()
        self.cleanup()

    def extract_archive(self) -> None:
        with zipfile.ZipFile(self._output) as zfile:
            dirname = os.path.dirname(zfile.namelist()[0])
            destpath = os.path.join(self._target_dir, dirname)
            if os.path.exists(destpath):
                if not self._exist_ok:
                    logger.warning("Cannot extract: '%s' already exists", destpath)
                    self.error = True
                    return
            try:
                zfile.extractall(self._target_dir)
                logger.debug(
                    f"Successfully downloaded and extracted to {destpath!r} from: {self.addr!r}",
                )
            except Exception as e:
                logger.error("Extract error: %s", e)
                self.error = True

    def cleanup(self) -> None:
        self._output.close()


class DownloadWrapper(QObject):
    done = pyqtSignal(object, object)

    def __init__(
            self,
            nam: QNetworkAccessManager,
            name: str,
            url: str,
            target_dir: str,
            delay_timer: QTimer | None,
    ) -> None:
        super().__init__()
        self.requests = set()
        self.name = name
        self._url = url
        self._nam = nam
        self._target_dir = target_dir
        self._delay_timer = delay_timer
        self._dl: FileDownload | None = None
        if delay_timer is None:
            self._start_download()
        else:
            delay_timer.timeout.connect(self._start_download)

    def _start_download(self) -> None:
        if self._delay_timer is not None:
            self._delay_timer.disconnect(self._start_download)
        self._dl = self._prepare_dl()
        self._dl.run()

    def _prepare_dl(self) -> FileDownload:
        filepath = os.path.join(self._target_dir, self.name)
        dl = FileDownload(filepath, self._nam, self._url)
        dl.finished.connect(self._finished)
        dl.blocksize = None
        return dl

    def remove_request(self, req: DownloadRequest) -> None:
        self.requests.remove(req)

    def add_request(self, req: DownloadRequest) -> None:
        self.requests.add(req)

    def _finished(self, dl: FileDownload) -> None:
        self.done.emit(self, dl.dest.fileName())

    def failed(self):
        return not self._dl.succeeded()


class DownloadRequest(QObject):
    done = pyqtSignal(object, object)

    def __init__(self):
        QObject.__init__(self)
        self._dl = None

    @property
    def dl(self):
        return self._dl

    @dl.setter
    def dl(self, value):
        if self._dl is not None:
            self._dl.remove_request(self)
        self._dl = value
        if self._dl is not None:
            self._dl.add_request(self)

    def finished(self, name, result):
        self.done.emit(name, result)


class Downloader(QObject):
    """
    Class for downloading. Clients ask to download by giving download
    requests, which are stored by name. After download is complete, all
    download requests get notified (neatly avoiding the 'requester died while
    we were downloading' issue).

    Requests can be resubmitted. That reclassifies them to a new name.
    """
    REDOWNLOAD_TIMEOUT = 5 * 60 * 1000
    DOWNLOAD_FAILS_TO_TIMEOUT = 3

    def __init__(self, target_dir: str) -> None:
        super().__init__()
        self._nam = QNetworkAccessManager(self)
        self._target_dir = target_dir
        self._downloads: dict[str, DownloadWrapper] = {}
        self._timeouts = DownloadTimeouts(self.REDOWNLOAD_TIMEOUT, self.DOWNLOAD_FAILS_TO_TIMEOUT)

    def set_target_dir(self, target_dir: str) -> None:
        self._target_dir = target_dir

    def download(self, name: str, request: DownloadRequest, url: str) -> None:
        self._add_request(name, request, url)

    def _add_request(self, name: str, req: DownloadRequest, url: str) -> None:
        if name not in self._downloads:
            self._add_download(name, url)
        dl = self._downloads[name]
        req.dl = dl

    def _add_download(self, name: str, url: str) -> None:
        if self._timeouts.on_timeout(name):
            delay = self._timeouts.timer
        else:
            delay = None
        dl = DownloadWrapper(self._nam, name, url, self._target_dir, delay)
        dl.done.connect(self._finished_download)
        self._downloads[name] = dl

    def _finished_download(self, download: DownloadWrapper, download_path: str) -> None:
        self._timeouts.update_fail_count(download.name, download.failed())
        requests = set(download.requests)  # Don't change it during iteration
        for req in requests:
            req.dl = None
        del self._downloads[download.name]
        for req in requests:
            req.finished(download.name, (download_path, download.failed()))


class DownloadTimeouts:
    def __init__(self, timeout_interval, fail_count_to_timeout):
        self._fail_count_to_timeout = fail_count_to_timeout
        self._timed_out_items = {}
        self.timer = QTimer()
        self.timer.setInterval(timeout_interval)
        self.timer.timeout.connect(self._clear_timeouts)

    def __getitem__(self, item):
        return self._timed_out_items.get(item, 0)

    def __setitem__(self, item, value):
        if value == 0:
            self._timed_out_items.pop(item, None)
        else:
            self._timed_out_items[item] = value

    def on_timeout(self, item):
        return self[item] >= self._fail_count_to_timeout

    def update_fail_count(self, item, failed):
        if failed:
            self[item] += 1
        else:
            self[item] = 0

    def _clear_timeouts(self):
        self._timed_out_items.clear()


class ImageDownloader:
    def __init__(self, save_dir: str = AVATARS_CACHE_DIR, size: QSize | None = None) -> None:
        self._size = size
        self._nam = QNetworkAccessManager()
        self._requests = {}
        self._nam.finished.connect(self._image_download_finished)
        self.save_dir = save_dir

    def image_path(self, url: QUrl | str) -> str:
        return os.path.join(self.save_dir, self.image_name(url))

    def image_exists(self, url: QUrl | str) -> bool:
        return os.path.isfile(self.image_path(url))

    def set_save_dir(self, save_dir: str) -> None:
        self.save_dir = save_dir

    def image_name(self, url: QUrl | str) -> str:
        return QUrl(url).fileName(QUrl.ComponentFormattingOption.EncodeSpaces)

    def download_image(self, url: str, req: DownloadRequest) -> None:
        self._add_request(url, req)

    def _add_request(self, url, req):
        should_download = url not in self._requests
        self._requests.setdefault(url, set()).add(req)
        if should_download:
            self._nam.get(QNetworkRequest(QUrl(url)))

    def _image_download_finished(self, reply: QNetworkReply) -> None:
        url_str = reply.url().toString()
        avatar_name = self.image_name(reply.url())
        avatar_path = self._save_image_to_cache(avatar_name, reply.readAll())

        reqs = self._requests.pop(url_str, [])
        for req in reqs:
            req.finished(url_str, QPixmap(avatar_path))

    def _save_image_to_cache(self, name: str, qbytes: QByteArray) -> str:
        filepath = os.path.join(self.save_dir, name)
        pixmap = QPixmap()
        pixmap.loadFromData(qbytes)
        if self._size is not None:
            pixmap.scaled(self._size).save(filepath)
        else:
            pixmap.save(filepath)
        return filepath


class CachedImageDownloader(ImageDownloader):
    def __init__(self, save_dir: str = AVATARS_CACHE_DIR, size: QSize | None = None) -> None:
        ImageDownloader.__init__(self, save_dir, size)
        self.images = {}
        self.load_cache()

    def load_cache(self) -> None:
        for filename in os.listdir(self.save_dir):
            filepath = os.path.join(self.save_dir, filename)
            pix = QPixmap(filepath)
            self.images[filename] = pix if self._size is None else pix.scaled(self._size)

    def has_image(self, name_or_url: QUrl | str) -> bool:
        return self.get_image(name_or_url) is not None

    def get_image(self, name_or_url: QUrl | str) -> QPixmap | None:
        return self.images.get(self.image_name(name_or_url))

    def download_if_needed(self, url: str | None, req: DownloadRequest) -> None:
        if url is None or self.has_image(url):
            return
        self.download_image(url, req)

    def _save_image_to_cache(self, name: str, qbytes: QByteArray) -> str:
        filepath = ImageDownloader._save_image_to_cache(self, name, qbytes)
        if name not in self.images:
            self.images[name] = QPixmap(filepath)
        return filepath


class MapPreviewDownloader(ImageDownloader):
    def __init__(self, target_dir: str, size_str: str, size: QSize | None = None) -> None:
        super().__init__(target_dir, size)
        self.size_str = size_str

    def download_preview(self, name: str, req: DownloadRequest) -> None:
        self._add_request(self._target_url(name), req)

    def _target_url(self, name: str) -> str:
        return Settings.get("vault/map_preview_url").format(size=self.size_str, name=name)


class MapSmallPreviewDownloader(MapPreviewDownloader):
    def __init__(self) -> None:
        super().__init__(MAP_PREVIEW_SMALL_DIR, "small")


class MapLargePreviewDownloader(MapPreviewDownloader):
    def __init__(self) -> None:
        super().__init__(MAP_PREVIEW_LARGE_DIR, "large")
