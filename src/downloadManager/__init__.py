from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5 import QtWidgets, QtCore
import urllib.request, urllib.error, urllib.parse
import logging
import os
import util
import warnings
from decorators import with_logger
from config import Settings


@with_logger
class FileDownload(object):
    """
    A simple async one-shot file downloader.
    """
    def __init__(self, nam, addr, dest, start=lambda _: None, progress=lambda _: None, finished=lambda _: None):
        self._nam = nam
        self.addr = addr
        self.dest = dest

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
        if self._dfile is not None:
            self._dfile.close()
            self._dfile = None
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

@with_logger
class downloadManager(QtCore.QObject):
    ''' This class allows downloading stuff in the background'''

    def __init__(self, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.client = parent
        self.nam = QNetworkAccessManager(self)

        self.modRequests = {}
        self.mapRequests = {}
        self.mapRequestsItem = []

    @QtCore.pyqtSlot(FileDownload)
    def finishedDownload(self, dler):
        urlstring = dler.addr
        name = os.path.basename(urlstring)
        self._logger.info("Finished download from " + urlstring)
        dler.dest.close()

        reqlist = []
        if urlstring in self.mapRequests: reqlist = self.mapRequests[urlstring]
        if urlstring in self.modRequests: reqlist = self.modRequests[urlstring]
        if not reqlist:
            dler.dest.remove()
            return

        if urlstring in self.mapRequests: del self.mapRequests[urlstring]
        if urlstring in self.modRequests: del self.modRequests[urlstring]

        #save the map from cache
        if not dler.succeeded():
            dler.dest.remove()
            pathimg = "games/unknown_map.png"
            self._logger.debug("Web Preview failed for: " + name)

        self._logger.debug("Web Preview used for: " + name)
        for requester in reqlist:
            if requester:
                if requester in self.mapRequestsItem:
                    requester.setIcon(0, util.THEME.icon(pathimg, False))
                    self.mapRequestsItem.remove(requester)
                else:
                    requester.setIcon(util.THEME.icon(pathimg, False))

    @QtCore.pyqtSlot(QNetworkReply.NetworkError)
    def downloadError(self, networkError):
        self._logger.info("Network Error")

    @QtCore.pyqtSlot()
    def readyRead(self):
        self._logger.info("readyRead")

    @QtCore.pyqtSlot(int, int)
    def progress(self, rcv, total):
        self._logger.info("received " + rcv + "out of" + total + " bytes")

    def _get_cachefile(self, name):
        pathimg = os.path.join(util.CACHE_DIR, name)
        img = QtCore.QFile(pathimg)
        img.open(QtCore.QIODevice.WriteOnly)
        return img

    def downloadMap(self, name, requester, item=False):
        '''
        Downloads a preview image from the web for the given map name
        '''
        #This is done so generated previews always have a lower case name. This doesn't solve the underlying problem (case folding Windows vs. Unix vs. FAF)
        name = name.lower()
        if len(name) == 0:
            return

        url = VAULT_PREVIEW_ROOT + urllib.parse.quote(name) + ".png"
        if not url in self.mapRequests:
            self._logger.info("Searching map preview for: " + name + " from " + url)
            self.mapRequests[url] = []

            img = self._get_cachefile(name)
            downloader = FileDownload(self.nam, url, img, finished = self.finishedDownload)
            downloader.blocksize = None
            downloader.run()

        self.mapRequests[url].append(requester)
        if item:
            self.mapRequestsItem.append(requester)

    def downloadModPreview(self, url, requester):
        if not url in self.modRequests:
            self._logger.debug("Searching mod preview for: " + os.path.basename(url).rsplit('.',1)[0])
            self.modRequests[url] = []

            img = self._get_cachefile(name)
            downloader = FileDownload(self.nam, url, img, finished = self.finishedDownload)
            downloader.blocksize = None
            downloader.run()

        self.modRequests[url].append(requester)
