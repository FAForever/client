from PyQt4 import QtCore, QtGui
from PyQt4 import QtWebKit
from stat import *
import util
import urllib
import logging
import os
import urllib2
import re
import json

logger = logging.getLogger("faf.replaysvault")
logger.setLevel(logging.DEBUG)

class ReplaysVault(QtCore.QObject):
    def __init__(self, client, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.client = client

        logger.debug("Replays Vault tab instantiating")
        
        self.ui = QtWebKit.QWebView()
                
        self.client.replaysVaultTab.layout().addWidget(self.ui)

        self.loaded = False
        self.client.showReplayVault.connect(self.reloadView)
        self.ui.loadFinished.connect(self.ui.show)

        
    @QtCore.pyqtSlot()
    def reloadView(self):
        if (self.loaded):
            return
        self.loaded = True
        
        self.ui.setVisible(False)

        #If a local theme CSS exists, skin the WebView with it
        if util.themeurl("vault/style.css"):
            self.ui.settings().setUserStyleSheetUrl(util.themeurl("vault/style.css"))
        self.ui.setUrl(QtCore.QUrl("http://www.faforever.com/webcontent/replayvault?username={user}&pwdhash={pwdhash}".format(user=self.client.login, pwdhash=self.client.password)))
        

        