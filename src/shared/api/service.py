import json

from PyQt4.QtCore import *
from PyQt4.QtNetwork import *


class RESTResponse(QObject):

    error = pyqtSignal(dict)
    done = pyqtSignal(dict)

    def __init__(self, reply):
        super(RESTResponse, self).__init__()

        self.reply = reply
        reply.finished.connect(self._onFinished)
        reply.downloadProgress.connect(self._onProgress)
        print reply.error()
        print reply.isRunning()

    def _onProgress(self, recv, total):
        print "OnProgress " + recv + " " + total

    def _onFinished(self):
        print "On Finished"
        resData = str(self.reply.readAll())
        print resData
        if self.reply.error():
            if len(resData) == 0:
                self.error.emit({'statusMessage': self.reply.errorString()})
            else:
                try:
                    self.error.emit(json.loads(resData))
                except ValueError: # Non-json response -> Server error
                    self.error.emit({'statusMessage': resData})

        else:
            resp = json.loads(resData)

            self.done.emit(resp)


class Service:
    def __init__(self, network_manager):
        self.network_manager = network_manager

    def _get(self, url):
        req = QNetworkRequest(QUrl(url))
        print url
        return RESTResponse(self.network_manager.get(req))

    def _post(self, url, post_data):
        req = QNetworkRequest(QUrl(url))
        req.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")

        return RESTResponse(self.network_manager.post(req, json.dumps(post_data).encode()))
