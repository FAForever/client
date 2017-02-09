from PyQt4 import QtCore
from PyQt4.QtCore import QObject, Qt

from .newsitem import NewsFrame
from .wpapi import WPAPI

import client

import math
import logging
logger = logging.getLogger(__name__)

class NewsManager(QObject):
    FRAMES = 5

    def __init__(self, client):
        QObject.__init__(self)
        self.newsContent = []
        self.newsFrames = []
        self.selectedFrame = None
        self.page = 0

        for i in range(self.FRAMES):
            frame = NewsFrame()
            self.newsFrames.append(frame)
            client.newsAreaLayout.addWidget(frame)
            frame.clicked.connect(self.frameClicked)

        client.nextPageButton.clicked.connect(self.nextPage)
        client.prevPageButton.clicked.connect(self.prevPage)
        client.pageBox.currentIndexChanged.connect(self.selectPage)

        self.WpApi = WPAPI(client)
        self.WpApi.newsDone.connect(self.on_wpapi_done)
        self.WpApi.download()

    @QtCore.pyqtSlot(list)
    def on_wpapi_done(self, items):
        """
        Reinitialize the whole news conglomerate after downloading the news from the api.

        items is a list of (title, content) tuples.

        We need to set up pagination and the news item frames.
        """
        self.newsContent = items

        self.npages = int(math.ceil(len(items) / self.FRAMES))
        self.page = 0

        pb = client.instance.pageBox
        pb.clear()
        pb.insertItems(0, ['Page {: >2}'.format(x + 1) for x in range(self.npages)])

        self.selectPage(0)

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
                frame.mf.doFilter = True

        selectedFrame.newsWebView.page().mainFrame().setScrollBarPolicy(Qt.Vertical, Qt.ScrollBarAsNeeded)
        selectedFrame.expand()
        selectedFrame.mf.doFilter = False

        self.selectedFrame = selectedFrame

    def resetFrames(self):
        logger.info('resetFrames')
        self.selectedFrame = None
        for frame in self.newsFrames:
            frame.expand()
            frame.newsWebView.page().mainFrame().setScrollBarPolicy(Qt.Vertical, Qt.ScrollBarAlwaysOff)
            frame.mf.doFilter = True


    def nextPage(self):
        self.selectPage(self.page + 1)

    def prevPage(self):
        self.selectPage(self.page - 1)

    @QtCore.pyqtSlot(int)
    def selectPage(self, idx):
        self.page = idx
        pb = client.instance.pageBox
        pb.setCurrentIndex(idx)

        client.instance.prevPageButton.setEnabled(True)
        client.instance.nextPageButton.setEnabled(True)

        if idx == 0:
            client.instance.prevPageButton.setEnabled(False)
        elif idx == self.npages - 1:
            client.instance.nextPageButton.setEnabled(False)

        firstNewsIdx = idx * self.FRAMES

        for frameIdx in range(self.FRAMES):
            nc = self.newsContent[frameIdx + firstNewsIdx]
            self.newsFrames[frameIdx].set_content(nc[0], nc[1])

        self.resetFrames()

