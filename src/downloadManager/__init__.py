from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5 import QtWidgets, QtCore
import urllib.request, urllib.error, urllib.parse
import logging
import os
import util
import warnings
from config import Settings

logger = logging.getLogger(__name__)


class FileDownload(object):
    """
    A simple async one-shot file downloader.
    """
    def __init__(self, nam, addr, dest, destpath=None,
                 start=lambda _: None, progress=lambda _: None, finished=lambda _: None):
        self._nam = nam
        self.addr = addr
        self.dest = dest
        self.destpath = destpath

        self.canceled = False
        self.error = False

        self.blocksize = 8192
        self.bytes_total = 0
        self.bytes_progress = 0

        self._dfile = None

        self.cb_start = start
        self.cb_progress = progress
        self.cb_finished = finished

        self._reading = False
        self._running = False
        self._sock_finished = False

    def _stop(self):
        ran = self._running
        self._running = False
        if ran:
            self._finish()

    def _error(self):
        self.error = True
        self._stop()

    def cancel(self):
        self.canceled = True
        self._stop()

    def _finish(self):
        # check status code
        statusCode = self._dfile.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if statusCode != 200:
            logger.warning('Download failed: %s -> %s', self.addr, statusCode)
            self.error = True
        self.cb_finished(self)

    def run(self):
        self._running = True
        req = QNetworkRequest(QtCore.QUrl(self.addr))
        req.setRawHeader(b'User-Agent', b"FAF Client")
        req.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
        req.setMaximumRedirectsAllowed(3)

        self.cb_start(self)

        self._dfile = self._nam.get(req)
        self._dfile.error.connect(self._error)
        self._dfile.finished.connect(self._atFinished)
        self._dfile.downloadProgress.connect(self._atProgress)
        self._dfile.readyRead.connect(self._kick_read)
        self._kick_read()

    def _atFinished(self):
        self._sock_finished = True
        self._kick_read()

    def _atProgress(self, recv, total):
        self.bytes_progress = recv
        self.bytes_total = total

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
            # Sock can be marked as finished either before read or inside readloop
            # Either way we've read everything after it was marked
            self._stop()

    def _readloop(self):
            bs = self.blocksize if self.blocksize is not None else self._dfile.bytesAvailable()
            self.dest.write(self._dfile.read(bs))
            self.cb_progress(self)

    def succeeded(self):
        return not self.error and not self.canceled

    def waitForCompletion(self):
        waitFlag = QtCore.QEventLoop.WaitForMoreEvents
        while self._running:
            QtWidgets.QApplication.processEvents(waitFlag)


VAULT_PREVIEW_ROOT = "{}/faf/vault/map_previews/small/".format(Settings.get('content/host'))


class downloadManager(QtCore.QObject):
    """ This class allows downloading stuff in the background"""

    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.client = parent
        self.nam = QNetworkAccessManager(self)

        self.modRequests = {}
        self.downloaders = set()

    @QtCore.pyqtSlot(FileDownload)
    def finishedDownload(self, dler):
        self.downloaders.remove(dler)
        dler.dest.close()
        urlstring = dler.addr

        # Remove '.part'
        partpath = dler.destpath
        filepath = partpath[:-5]
        QtCore.QDir().rename(partpath, filepath)

        local_path = False
        filename = os.path.basename(filepath)
        logger.info("Finished download from " + urlstring)

        reqlist = []
        if urlstring in self.modRequests:
            reqlist = self.modRequests[urlstring]
        if not reqlist:
            dler.dest.remove()
            return

        if urlstring in self.modRequests:
            del self.modRequests[urlstring]

        if not dler.succeeded():
            dler.dest.remove()
            os.unlink(filepath)
            filepath = "games/unknown_map.png"
            local_path = True
            logger.debug("Web Preview failed for: " + filename)
        else:
            logger.debug("Web Preview used for: " + filename)

        for requester in reqlist:
            if requester:
                requester.setIcon(util.THEME.icon(filepath, local_path))

    def _get_cachefile(self, name):
        imgpath = os.path.join(util.CACHE_DIR, name)
        img = QtCore.QFile(imgpath)
        img.open(QtCore.QIODevice.WriteOnly)
        return img, imgpath

    def downloadModPreview(self, url, name, requester):
        if not url in self.modRequests:
            logger.debug("Searching mod preview for: " + str(os.path.basename(url).rsplit('.', 1)[0]))
            self.modRequests[url] = []

            img, imgpath = self._get_cachefile(name + '.part')
            downloader = FileDownload(self.nam, url, img, imgpath, finished=self.finishedDownload)
            self.downloaders.add(downloader)
            downloader.blocksize = None
            downloader.run()

        self.modRequests[url].append(requester)


class MapDownload(QtCore.QObject):
    done = QtCore.pyqtSignal(object, object)

    def __init__(self, nam, mapname, url, delay_timer=None):
        QtCore.QObject.__init__(self)
        self.requests = set()
        self.mapname = mapname
        self._url = url
        self._nam = nam
        self._delay_timer = delay_timer
        self._dl = None
        if delay_timer is None:
            self._start_download()
        else:
            delay_timer.timeout.connect(self._start_download)

    def _download_url(self):
        if self._url is not None:
            return self._url
        return VAULT_PREVIEW_ROOT + urllib.parse.quote(self.mapname) + ".png"

    def _start_download(self):
        if self._delay_timer is not None:
            self._delay_timer.disconnect(self._start_download)
        self._dl = self._prepare_dl(self._nam, self.mapname)
        self._dl.run()

    def _prepare_dl(self, nam, mapname):
        url = self._download_url()
        img, imgpath = self._get_cachefile(mapname + ".png.part")
        dl = FileDownload(nam, url, img, imgpath)
        dl.cb_finished = self._finished
        dl.blocksize = None
        return dl

    def _get_cachefile(self, name):
        imgpath = os.path.join(util.CACHE_DIR, name)
        img = QtCore.QFile(imgpath)
        img.open(QtCore.QIODevice.WriteOnly)
        return img, imgpath

    def remove_request(self, req):
        self.requests.remove(req)

    def add_request(self, req):
        self.requests.add(req)

    def _finished(self, dl):
        dl.dest.close()
        logger.info("Finished download from " + dl.addr)
        if self.failed():
            logger.debug("Web Preview failed for: {}".format(self.mapname))
            os.unlink(dl.destpath)
            filepath = "games/unknown_map.png"
            is_local = True
        else:
            logger.debug("Web Preview used for: {}".format(self.mapname))
            # Remove '.part'
            partpath = dl.destpath
            filepath = partpath[:-5]
            QtCore.QDir().rename(partpath, filepath)
            is_local = False
        self.done.emit(self, (filepath, is_local))

    def failed(self):
        return not self._dl.succeeded()


class MapDownloadRequest(QtCore.QObject):
    done = QtCore.pyqtSignal(object, object)

    def __init__(self):
        QtCore.QObject.__init__(self)
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

    def finished(self, mapname, result):
        self.done.emit(mapname, result)


class MapDownloader(QtCore.QObject):
    """
    Class for downloading maps. Clients ask to download by giving download
    requests, which are stored by mapname. After download is complete, all
    download requests get notified (neatly avoiding the 'requester died while
    we were downloading' issue).

    Requests can be resubmitted. That reclassifies them to a new mapname.
    """
    MAP_REDOWNLOAD_TIMEOUT = 5 * 60 * 1000
    MAP_DOWNLOAD_FAILS_TO_TIMEOUT = 3

    def __init__(self):
        QtCore.QObject.__init__(self)
        self._nam = QNetworkAccessManager(self)
        self._downloads = {}
        self._timeouts = DownloadTimeouts(self.MAP_REDOWNLOAD_TIMEOUT,
                                          self.MAP_DOWNLOAD_FAILS_TO_TIMEOUT)

    def download_map(self, mapname, req, url=None):
        self._add_request(mapname, req, url)

    def _add_request(self, mapname, req, url):
        if mapname not in self._downloads:
            self._add_download(mapname, url)
        dl = self._downloads[mapname]
        req.dl = dl

    def _add_download(self, mapname, url):
        if self._timeouts.on_timeout(mapname):
            delay = self._timeouts.timer
        else:
            delay = None
        dl = MapDownload(self._nam, mapname, url, delay)
        dl.done.connect(self._finished_download)
        self._downloads[mapname] = dl

    def _finished_download(self, dl, result):
        self._timeouts.update_fail_count(dl.mapname, dl.failed())
        requests = set(dl.requests)     # Don't change it during iteration
        for req in requests:
            req.dl = None
        del self._downloads[dl.mapname]
        for req in requests:
            req.finished(dl.mapname, result)


class DownloadTimeouts:
    def __init__(self, timeout_interval, fail_count_to_timeout):
        self._fail_count_to_timeout = fail_count_to_timeout
        self._timed_out_items = {}
        self.timer = QtCore.QTimer()
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


# Temporary utility class for catching download callbacks
class IconCallback:
    def __init__(self, mapname, cb):
        self.mapname = mapname
        self.cb = cb

    def setIcon(self, icon):
        self.cb(self.mapname, icon)
