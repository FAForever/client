from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt4 import QtCore

import json
import logging
import sys

logger = logging.getLogger(__name__)

#FIXME: Make setting
WPAPI_ROOT = 'http://direct.faforever.com/wp-json/wp/v2/posts?per_page={perpage}&page={page}&_embed=1'

class WPAPI(QtCore.QObject):
    newsDone = QtCore.pyqtSignal(list)

    def __init__(self, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.nam = QNetworkAccessManager(self)

        self.nam.finished.connect(self.finishedDownload)

    @QtCore.pyqtSlot(QNetworkReply)
    def finishedDownload(self, reply):
        ''' finishing downloads '''
        # mark reply for collection by Qt
        reply.deleteLater()


        logger.info('Received {}'.format(reply.url().toString()))

        try:
            content = reply.readAll()

            js = json.loads(str(content))

            posts = []

            for post in js:
                content = {
                    'title': post.get('title', {}).get('rendered'),
                    'body': post.get('content', {}).get('rendered'),
                    'date': post.get('date'),
                    'excerpt': post.get('excerpt', {}).get('rendered'),
                    'author': post.get('_embedded', {}).get('author')
                }
                posts.append(content)

            self.newsDone.emit(posts)
        except:
            logger.exception('Error handling wp data')

    def download(self, page=1, perpage=10):
        url = QtCore.QUrl(WPAPI_ROOT.format(page=page,perpage=perpage))
        request = QNetworkRequest(url)
        self.nam.get(request)

