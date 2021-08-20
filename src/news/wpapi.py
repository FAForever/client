import json
import logging

from PyQt5 import QtCore
from PyQt5.QtNetwork import (
    QNetworkAccessManager, QNetworkReply, QNetworkRequest,
)

from config import Settings

logger = logging.getLogger(__name__)

# FIXME: Make setting
WPAPI_ROOT = (
    '{host}/wp-json/wp/v2/posts?per_page={perpage}&page={page}&_embed=1'
)


class WPAPI(QtCore.QObject):
    newsDone = QtCore.pyqtSignal(list)

    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.nam = QNetworkAccessManager(self)

        self.nam.finished.connect(self.finishedDownload)

    @QtCore.pyqtSlot(QNetworkReply)
    def finishedDownload(self, reply):
        """ finishing downloads """
        # mark reply for collection by Qt
        reply.deleteLater()

        logger.info('Received {}'.format(reply.url().toString()))

        try:
            content = reply.readAll()

            js = json.loads(bytes(content).decode('utf-8'))

            posts = []

            for post in js:
                content = {
                    'title': post.get('title', {}).get('rendered'),
                    'body': post.get('content', {}).get('rendered'),
                    'date': post.get('date'),
                    'excerpt': post.get('excerpt', {}).get('rendered'),
                    'author': post.get('_embedded', {}).get('author'),
                    'link': post.get('link'),
                    'external_link': post.get('newshub_externalLinkUrl'),
                    'img_url': (
                        post.get('_embedded', {})
                        .get('wp:featuredmedia', [{}])[0]
                        .get('source_url', "")
                    ),
                }
                posts.append(content)

            self.newsDone.emit(posts)
        except BaseException:
            logger.exception('Error handling wp data')

    def download(self, page=1, perpage=10):
        url = QtCore.QUrl(
            WPAPI_ROOT.format(
                host=Settings.get('news/host'), page=page, perpage=perpage,
            ),
        )
        request = QNetworkRequest(url)
        request.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
        self.nam.get(request)
