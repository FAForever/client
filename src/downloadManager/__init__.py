#-------------------------------------------------------------------------------
# Copyright (c) 2013 Gael Honorez.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------

from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt4 import QtGui, QtCore
import urllib2
import logging
import os
import util
import warnings

logger= logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

VAULT_PREVIEW_ROOT = "http://content.faforever.com/faf/vault/map_previews/small/"

class downloadManager(QtCore.QObject):
    ''' This class allows downloading stuff in the background'''
    
    def __init__(self, parent = None):
        self.client = parent
        self.nam = QNetworkAccessManager()
        
        self.nam.finished.connect(self.finishedDownload)

        self.modRequests = {}
        self.mapRequests = {}
        self.mapRequestsItem = []
        
    def finishedDownload(self,reply):
        ''' finishing downloads '''
        urlstring = reply.url().toString()
        reqlist = []
        if urlstring in self.mapRequests: reqlist = self.mapRequests[urlstring]
        if urlstring in self.modRequests: reqlist = self.modRequests[urlstring]
        if reqlist:
            #save the map from cache
            name = os.path.basename(reply.url().toString())
            pathimg = os.path.join(util.CACHE_DIR, name)
            img = QtCore.QFile(pathimg)
            img.open(QtCore.QIODevice.WriteOnly)
            img.write(reply.readAll())
            img.close()
            if os.path.exists(pathimg):
                #Create alpha-mapped preview image
                try:
                    pass # the server already sends 100x100 pic
#                    img = QtGui.QImage(pathimg).scaled(100,100)
#                    img.save(pathimg)
                except:
                    pathimg = "games/unknown_map.png"
                    logger.info("Failed to resize " + name)
            else :
                pathimg = "games/unknown_map.png"
                logger.debug("Web Preview failed for: " + name)
            logger.debug("Web Preview used for: " + name)
            for requester in reqlist:
                if requester:
                    if requester in self.mapRequestsItem:
                        requester.setIcon(0, util.icon(pathimg, False))
                        self.mapRequestsItem.remove(requester)
                    else:
                        requester.setIcon(util.icon(pathimg, False))
            if urlstring in self.mapRequests: del self.mapRequests[urlstring]
            if urlstring in self.modRequests: del self.modRequests[urlstring]
            
    def downloadMap(self, name, requester, item=False):
        '''
        Downloads a preview image from the web for the given map name
        '''
        #This is done so generated previews always have a lower case name. This doesn't solve the underlying problem (case folding Windows vs. Unix vs. FAF)
        name = name.lower()
        if len(name) == 0:
            return
        

        url = QtCore.QUrl(VAULT_PREVIEW_ROOT + urllib2.quote(name) + ".png")
        if not url.toString() in self.mapRequests:
            logger.debug("Searching map preview for: " + name)
            self.mapRequests[url.toString()] = []
            request = QNetworkRequest(url)
            self.nam.get(request)
            self.mapRequests[url.toString()].append(requester)
        else :
            self.mapRequests[url.toString()].append(requester)
        if item:
            self.mapRequestsItem.append(requester)

    def downloadModPreview(self, strurl, requester):
        url = QtCore.QUrl(strurl)
        if not url.toString() in self.modRequests:
            logger.debug("Searching mod preview for: " + os.path.basename(strurl).rsplit('.',1)[0])
            self.modRequests[url.toString()] = []
            request = QNetworkRequest(url)
            self.nam.get(request)
        self.modRequests[url.toString()].append(requester)
