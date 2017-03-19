from PyQt5 import QtCore
from PyQt5.QtCore import QObject, Qt

from .newsitem import NewsItem
from .wpapi import WPAPI

import client

import math
import logging
logger = logging.getLogger(__name__)

class NewsManager(QObject):
    FRAMES = 5

    def __init__(self, client):
        QObject.__init__(self)
        self.widget = client
#        self.newsContent = []
#        self.newsFrames = []
#        self.selectedFrame = None
#        self.page = 0
#
#        for i in range(self.FRAMES):
#            frame = NewsFrame()
#            self.newsFrames.append(frame)
#            client.newsAreaLayout.addWidget(frame)
#            frame.clicked.connect(self.frameClicked)
#
#        client.nextPageButton.clicked.connect(self.nextPage)
#        client.prevPageButton.clicked.connect(self.prevPage)
#        client.pageBox.currentIndexChanged.connect(self.selectPage)

        self.WpApi = WPAPI(client)
        self.WpApi.newsDone.connect(self.on_wpapi_done)
        self.WpApi.download(page=1, perpage=20)

    @QtCore.pyqtSlot(list)
    def on_wpapi_done(self, items):
        """
        Reinitialize the whole news conglomerate after downloading the news from the api.

        items is a list of (title, content) tuples.

        We need to set up pagination and the news item frames.
        """
        for item in items:
            self.widget.addNews(item)
        self.widget.newsList.setCurrentItem(self.widget.newsList.item(0))
#        self.newsContent = self.newsContent + items
#
#        self.npages = int(math.ceil(len(self.newsContent) / self.FRAMES))
#
##        origpage = self.page
#
#        pb = client.instance.pageBox
#        pb.insertItems(pb.count(), ['Page {: >2}'.format(x + 1) for x in range(pb.count(), self.npages)])
#
#        self.selectPage(self.page)

    @QtCore.pyqtSlot()
    def frameClicked(self):
        sender = self.sender()
        logger.info("Sender: {}".format(sender))
        logger.info("Clicked '{}'".format(sender.content[0]))
        # unexpanded frame - expand
        if self.selectedFrame != sender:
            self.expandFrame(sender)
        # expanded frame - unexpand if click not in webview
        else:
            if not sender.newsWebView.underMouse():
                self.resetFrames()

    def expandFrame(self, selectedFrame):
        if self.selectedFrame is not None:
            self.selectedFrame.collapse()
            self.selectedFrame.mf.doFilter = True
        else:
            for frame in self.newsFrames:
                frame.collapse()

        selectedFrame.expand(Qt.ScrollBarAsNeeded, set_filter=False)

        self.selectedFrame = selectedFrame

    def resetFrames(self):
        logger.info('resetFrames')
        self.selectedFrame = None
        for frame in self.newsFrames:
            frame.expand(Qt.ScrollBarAlwaysOff, set_filter=True)

    def nextPage(self):
        pb = client.instance.pageBox
        pb.setCurrentIndex(self.page + 1)

    def prevPage(self):
        pb = client.instance.pageBox
        pb.setCurrentIndex(self.page - 1)

    @QtCore.pyqtSlot(int)
    def selectPage(self, idx):
        logger.info('selectPage')
        self.page = idx

        client.instance.prevPageButton.setEnabled(True)
        client.instance.nextPageButton.setEnabled(True)

        if idx == 0:
            client.instance.prevPageButton.setEnabled(False)
        elif idx == self.npages - 1:
            client.instance.nextPageButton.setEnabled(False)
            # download next page
            self.WpApi.download(page=self.npages+1, perpage=self.FRAMES)

        firstNewsIdx = idx * self.FRAMES

        for frameIdx in range(self.FRAMES):
            nc = self.newsContent[frameIdx + firstNewsIdx]
            self.newsFrames[frameIdx].set_content(nc[0], nc[1])

        self.resetFrames()

