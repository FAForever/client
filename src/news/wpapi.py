from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt4 import QtCore

import json
import logging
import sys

logger = logging.getLogger(__name__)

#FIXME: Make setting
WPAPI_ROOT = 'http://direct.faforever.com/wp-json/wp/v2/posts?per_page=30'

class WPAPI(QtCore.QObject):
    newsDone = QtCore.pyqtSignal(list)

    def __init__(self, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.client = parent
        self.nam = QNetworkAccessManager(self)

        self.nam.finished.connect(self.finishedDownload)

    @QtCore.pyqtSlot(QNetworkReply)
    def finishedDownload(self, reply):
        ''' finishing downloads '''
        # mark reply for collection by Qt
        reply.deleteLater()

        logger.info('Downloaded news from {}'.format(reply.url().toString()))

        try:
            content = reply.readAll()

            js = json.loads(unicode(content))

            posts = []

            for post in js:
                title = post.get('title', {}).get('rendered')
                body = post.get('content', {}).get('rendered')
                posts.append((title, body))

            self.newsDone.emit(posts)
        except:
            logger.exception('Error handling wp data')

    def download(self):
        url = QtCore.QUrl(WPAPI_ROOT)
        request = QNetworkRequest(url)
        self.nam.get(request)

