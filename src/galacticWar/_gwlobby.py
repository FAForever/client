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

from PyQt4 import QtGui, QtCore, QtNetwork
from galacticWar import logger, LOBBY_PORT, LOBBY_HOST, TEXTURE_SERVER, RANKS, FACTIONS
from galaxy import Galaxy
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest

from client import ClientState
from gwchannel import gwChannel
import util
import util.slpp
import fa

import zipfile
import StringIO

from util import GW_TEXTURE_DIR
import json
import os

from types import IntType, FloatType, ListType, DictType
import loginwizards

FormClass, BaseClass = util.loadUiType("galacticwar/galacticwar.ui")

class LobbyWidget(FormClass, BaseClass):
    planetClicked                   = QtCore.pyqtSignal(int)
    hovering                        = QtCore.pyqtSignal()
    creditsUpdated                  = QtCore.pyqtSignal(int)
    rankUpdated                     = QtCore.pyqtSignal(int)
    creditsUpdated                  = QtCore.pyqtSignal(int)
    victoriesUpdated                = QtCore.pyqtSignal(int)
    attacksUpdated                  = QtCore.pyqtSignal()
    planetUpdated                   = QtCore.pyqtSignal()
    attackProposalUpdated           = QtCore.pyqtSignal(int)
    temporaryReinforcementUpdated   = QtCore.pyqtSignal(dict)

    def __init__(self, client, *args, **kwargs):
        logger.debug("Lobby instantiating.")
        BaseClass.__init__(self, *args, **kwargs)
        
        self.setupUi(self)
        
        
        self.client = client
        #self.client.galacticwarTab.setStyleSheet(util.readstylesheet("galacticwar/galacticwar.css"))        
        self.client.galacticwarTab.layout().addWidget(self)
   
        self.downloader     = QNetworkAccessManager(self)
        self.downloader.finished.connect(self.finishRequest)
        
        self.shaderlist     =   []
        self.texturelist    =   {}        
        self.shaders    =   {}
        
        self.infoPanel  = None
        self.OGLdisplay = None
        
        self.galaxy     = Galaxy()
        self.channel    = None
        
        self.initDone   = False
        
        self.uid        = None
        self.faction    = None
        self.name       = None
        self.rank       = None
        self.credits    = 0
        self.victories  = 0
   
        self.attacks = {}
   
        self.state = ClientState.NONE
        
        ## Network initialization
        
        self.socket = QtNetwork.QTcpSocket()
        self.socket.readyRead.connect(self.readFromServer)
        self.socket.disconnected.connect(self.disconnectedFromServer)
        self.socket.error.connect(self.socketError)
        self.blockSize = 0     


        self.progress = QtGui.QProgressDialog()
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)

#    def focusEvent(self, event):
#        return BaseClass.focusEvent(self, event)
    
    def showEvent(self, event):
        if self.state != ClientState.ACCEPTED :
            if self.doConnect() :
                logger.info("connection not done")
                self.doLogin()                    
        
        else :
            if not self.initDone :
                logger.info("init not done")
                self.doLogin()
            else :
                if self.faction == None :
                    logger.info("not faction")
                    self.doLogin()

        return BaseClass.showEvent(self, event)

    def createChannel(self, chat, name):
        self.channel = gwChannel(chat, name, True)        

    def finishRequest(self, reply):
        filename = reply.url().toString().rsplit('/',1)[1]
        root, _ = os.path.splitext(filename)
        
        toFile = os.path.join(GW_TEXTURE_DIR, filename)
        writeFile = QtCore.QFile(toFile)
        if(writeFile.open(QtCore.QIODevice.WriteOnly)) :
                writeFile.write(reply.readAll())
                writeFile.close()                
        else:
            logger.warn("%s is not writeable in in %s. Skipping." % (filename, GW_TEXTURE_DIR))

        if root in self.texturelist :
            del self.texturelist[root]
            
        if len(self.texturelist) == 0:
            self.setup()
            self.progress.close()


    def doConnect(self):
        logger.debug("Connecting to server")
        if self.client.state == ClientState.ACCEPTED :

            self.progress.setCancelButtonText("Cancel")
            self.progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
            self.progress.setAutoClose(False)
            self.progress.setAutoReset(False)
            self.progress.setModal(1)
            self.progress.setWindowTitle("Galactic War Network...")
            self.progress.setLabelText("Gating in ...")
            self.progress.show()                
                      
             
#            self.login = self.client.login.strip()      
#            logger.info("Attempting to gate as: " + str(self.client.login))
            self.state = ClientState.NONE

            # Begin connecting.        
            self.socket.setSocketOption(QtNetwork.QTcpSocket.KeepAliveOption, 1)
            self.socket.connectToHost(LOBBY_HOST, LOBBY_PORT)
            
            
            
            while (self.socket.state() != QtNetwork.QAbstractSocket.ConnectedState) and self.progress.isVisible():
                QtGui.QApplication.processEvents()                                        
    
            self.state = ClientState.NONE    

    #        #Perform Version Check first        
            if not self.socket.state() == QtNetwork.QAbstractSocket.ConnectedState:
                
                self.progress.close() # in case it was still showing...
                # We either cancelled or had a TCP error, meaning the connection failed..
                if self.progress.wasCanceled():
                    logger.warn("doConnect() aborted by user.")
                else:
                    logger.error("doConnect() failed with clientstate " + str(self.state) + ", socket errorstring: " + self.socket.errorString())
                return False
            else:     
      
                return True  


    def doLogin(self):
        ''' login in the GW server 
            We are using the main login and session to check legitimity of the client.
        '''
        
        self.progress.setLabelText("Gating in...")
        self.progress.reset()
        self.progress.show()                       
   
        logger.info("Attempting to gate as: " + str(self.client.login))
        self.state = ClientState.NONE

        self.send(dict(command="hello", version=util.VERSION_STRING, port= self.client.gamePort, login=self.client.login, session = self.client.session, init = self.initDone))
        
        while (not self.state) and self.progress.isVisible():
            QtGui.QApplication.processEvents()
            

        if self.progress.wasCanceled():
            logger.warn("Gating aborted by user.")
            return False
        
        self.progress.close()

        if self.state == ClientState.ACCEPTED:
            logger.info("Gating accepted.")
            self.progress.close()
            return True   
            #self.connected.emit()            
          
        elif self.state == ClientState.REJECTED:
            logger.warning("Gating rejected.")
            return False
        else:
            # A more profound error has occurrect (cancellation or disconnection)
            return False



    def setup(self):
        self.galaxy.computeVoronoi()
        from glDisplay import GLWidget
        from infopanel import InfoPanelWidget
        from newsTicker import NewsTicker
        from reinforcements import TemporaryWidget
        #items panels
        self.temporaryItems = TemporaryWidget(self)
        self.OGLdisplay = GLWidget(self)
        self.newsTicker = NewsTicker(self)
        self.galaxyLayout.addWidget(self.OGLdisplay)
        self.galaxyLayout.addWidget(self.newsTicker)
        self.newsTicker.setMaximumHeight(20)
        self.newsTicker.updateText()
        self.infoPanel = InfoPanelWidget(self)
        self.info_Panel.layout().addWidget(self.infoPanel)

        self.send(dict(command = "init_done", status=True))
                
    def get_rank(self, faction, rank):
        return RANKS[faction][rank]


    def handle_welcome(self, message):
        self.state = ClientState.ACCEPTED

    def handle_reinforcement_info(self, message):
        '''populate reinforcement lists'''
        if message["temporary"] is True:
            self.temporaryReinforcementUpdated.emit(message)

    def handle_resource_required(self, message):
        if message["action"] == "shaders" :
            self.shaderlist = message["data"]
            self.send(dict(command = "request", action ="shaders"))
        elif message["action"] == "textures" :
            for tex in message["data"] :
                if not tex in self.texturelist :
                    self.texturelist[tex] = message["data"][tex]

        

    def handle_shader(self, message):
        name             = message["name"]
        shader_fragment  = message["shader_fragment"]
        shader_vertex    = message["shader_vertex"]
        if not name in self.shaders :
            self.shaders[name] = {}
            self.shaders[name]["fragment"]  = shader_fragment
            self.shaders[name]["vertex"]    = shader_vertex
        
        if name in self.shaderlist :
            self.shaderlist.remove(name)
        self.check_resources()
            
            #we have all our shader.
            
    
    def get_texture_name(self, tex):
        return os.path.join(GW_TEXTURE_DIR, tex + ".png")
    
    def download_textures(self):
        self.progress.show()
        self.progress.setLabelText("Downloading resources ...")
        
        textInCache = []
        
        for tex in self.texturelist : 
            if os.path.exists(self.get_texture_name(tex)) :
                if util.md5(self.get_texture_name(tex)) == self.texturelist[tex] :
                    logger.debug(tex + ".png in cache.")
                    textInCache.append(tex)
                    continue
            logger.debug("Downloading " + tex + ".png")
            self.downloader.get(QNetworkRequest(QtCore.QUrl(TEXTURE_SERVER + tex + ".png")))    
        
        for tex in textInCache :
            del self.texturelist[tex]
        
        if len(self.texturelist) == 0 :
            self.progress.close()
            self.setup()
             
        

    
    def check_resources(self):
        '''checking if we have everything we need'''
        if len(self.shaderlist) == 0 and self.initDone :
            self.download_textures()
    
    
    def handle_news_feed(self, message):
        '''Adding news to news feed'''
        self.newsTicker.addNews(message["news"])
    
    def handle_player_info(self, message):
        ''' Update Player stats '''
        
        self.uid        = int(message["uid"])
        self.faction    = message["faction"]
        self.name       = message["name"]        
        self.rank       = message["rank"]
        self.credits    = message["credits"]
        self.victories  = message["victories"]        
        
        logger.debug("Received player info : victories %i, credits %i" % (self.victories, self.credits))
       
        self.rankUpdated.emit(self.rank)
        self.creditsUpdated.emit(self.credits)
        self.victoriesUpdated.emit(self.victories)
    
    def handle_game_upgrades(self, message):
        '''writing reinforcement list'''
        upgrades = message["upgrades"]
        destination = os.path.join(util.APPDATA_DIR, "gamedata", "gwReinforcementList.gw")
        gwFile = QtCore.QFile(destination)
        gwFile.open(QtCore.QIODevice.WriteOnly)
        lua = util.slpp.SLPP()
        s = StringIO.StringIO()  
        z = zipfile.ZipFile(s, 'w')  
        z.writestr('gwReinforcementList/gwReinforcementList.lua', str(lua.encodeReinforcements(upgrades))) 
        z.close()
        gwFile.write(s.getvalue())
        gwFile.close()
        s.close()
    
    def handle_attack_result(self, message):
        self.progress.close()
        result = message["result"]
        if result == "won" :
            QtGui.QMessageBox.information(self, "War report", "You win !" , QtGui.QMessageBox.Close)
            
            
    def handle_attack_proposal(self, message):
        planetuid = message["planetuid"]
        self.attackProposalUpdated.emit(planetuid)
    
    def handle_attacks_info(self, message):
        logger.debug("updating attacks infos")
        attacks = message["attacks"]
        self.attacks = {}
        
        for playeruid in attacks :
            playeruid_int = int(playeruid)
            if not playeruid_int in self.attacks :
                self.attacks[playeruid_int] = {}
            
            for planetuid in attacks[playeruid] :
                planetuid_int = int(planetuid)
                self.attacks[playeruid_int][planetuid_int] = attacks[playeruid][planetuid]
        self.attacksUpdated.emit()

    def handle_planet_info(self, message):
        logger.debug("updating planet infos")
        uid = message['uid'] 
        if not uid in self.galaxy.control_points :
            x           = message['posx']
            y           = message['posy']
            size        = message['size']
            texture     = message['texture']
            textureMd5  = message['md5tex']
            name        = message['name']
            desc        = message['desc']
            
            if not texture in self.texturelist :
                self.texturelist[texture] = textureMd5 
            
            self.galaxy.addPlanet(uid, name, desc, x, y, size, texture = texture, init=True) 
            self.galaxy.update(message)
            
            if not uid in self.galaxy.links :
                self.galaxy.links[uid] = message['links']
        else :
            self.galaxy.update(message)
            self.planetUpdated.emit()

    def handle_logged_in(self, message):
       
        self.handle_player_info(message)
        if self.faction != None :
            self.client.galacticwarTab.setStyleSheet(util.readstylesheet("galacticwar/galacticwar.css").replace("%FACTION%", FACTIONS[self.faction]))   
            
        self.attacksUpdated.emit()

    def handle_create_account(self, message):
        if message["action"] == 0 :
            
            accountCreator = loginwizards.gwSelectFaction(self)
            accountCreator.exec_()
            if self.faction != None :
                self.send(dict(command = "account_creation", action = 0, faction = self.faction))
            else :
                self.client.mainTabs.setCurrentIndex(0)
                QtGui.QMessageBox.warning(self, "No faction :(", "You need to pledge allegiance to a faction in order to play Galactic War !")

        elif message["action"] == 1 :
            name = message["name"]
            self.faction = message["faction"]

            self.rank = message["rank"]
            
            question = QtGui.QMessageBox.question(self, "Avatar name generation", "Your avatar name will be : <br><br>" + self.get_rank(self.faction, self.rank) + " " + name + ".<br><br>Press Reset to generate another, Ok to accept.", QtGui.QMessageBox.Reset, QtGui.QMessageBox.Ok)
            if question ==  QtGui.QMessageBox.Reset :
                self.send(dict(command = "account_creation", action = 1))
            else :
                self.name = name
                self.send(dict(command = "account_creation", action = 2))
    
    def handle_init_done(self, message):
        if message['status'] == True :
            self.initDone = True
            self.check_resources()

    def handle_social(self, message):      
        if "autojoin" in message :
            if message["autojoin"] == 0 :
                self.client.autoJoin.emit(["#UEF"])
            elif message["autojoin"] == 1 :         
                self.client.autoJoin.emit(["#Aeon"])
            elif message["autojoin"] == 2 :
                self.client.autoJoin.emit(["#Cybran"])
            elif message["autojoin"] == 3 :
                self.client.autoJoin.emit(["#Seraphim"])

    def handle_searching(self, message):
        state = message["state"]
        if state == "on" :
            text = message["text"]
            self.progress.show()
            self.progress.setCancelButton(None)
            self.progress.setLabelText(text)
        else :
            self.progress.hide()

    def handle_notice(self, message):
        self.client.handle_notice(message)
        

    def handle_update(self, message):
        update = message["update"]
        if not util.developer():
            logger.warn("Server says that Updating is needed.")
            self.progress.close()
            self.state = ClientState.OUTDATED
            fa.updater.fetchClientUpdate(update)        

    def process(self, action, stream):
        if action == "PING":
            self.writeToServer("PONG")
        else :
            self.dispatchJSON(action, stream)
            
    
    def dispatchJSON(self, data_string, stream):
        '''
        A fairly pythonic way to process received strings as JSON messages.
        '''
        message = json.loads(data_string)
        cmd = "handle_" + message['command']
        logger.debug("Incoming JSON Message: " + data_string)
        if hasattr(self, cmd):
            getattr(self, cmd)(message)  
        else:
            logger.error("command unknown : %s", cmd)
 

    def send(self, message):
        data = json.dumps(message)
        logger.info("Outgoing JSON Message: " + data)
        self.writeToServer(data)

    @QtCore.pyqtSlot()
    def readFromServer(self):
        ins = QtCore.QDataStream(self.socket)        
        ins.setVersion(QtCore.QDataStream.Qt_4_2)
        
        while ins.atEnd() == False :
            if self.blockSize == 0:
                if self.socket.bytesAvailable() < 4:
                    return
                self.blockSize = ins.readUInt32()            
            if self.socket.bytesAvailable() < self.blockSize:
                return
            
            action = ins.readQString()
            self.process(action, ins)
            self.blockSize = 0
                                
            
    @QtCore.pyqtSlot()
    def disconnectedFromServer(self):
        logger.warn("Disconnected from lobby server.")

        if self.state == ClientState.ACCEPTED:
            QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(), "Disconnected from Galactic War", "The lobby lost the connection to the Galactic War server.<br/><b>You might still be able to chat.<br/>To play, try reconnecting a little later!</b>", QtGui.QMessageBox.Close)
                            
            self.client.mainTabs.setCurrentIndex(0)

            self.client.mainTabs.setTabEnabled(self.client.mainTabs.indexOf(self.client.galacticwarTab  ), False)
            self.client.mainTabs.setTabText(self.client.mainTabs.indexOf(self.client.galacticwarTab  ), "offline")
                
        self.state = ClientState.DROPPED             
            
    def writeToServer(self, action, *args, **kw):
        '''
        This method is the workhorse of the client, and is used to send messages, queries and commands to the server.
        '''
        logger.debug("Client: " + action)
        
        block = QtCore.QByteArray()
        out = QtCore.QDataStream(block, QtCore.QIODevice.ReadWrite)
        out.setVersion(QtCore.QDataStream.Qt_4_2)

        out.writeUInt32(0)
        out.writeQString(action)
   
        
        for arg in args :
            if type(arg) is IntType:
                out.writeInt(arg)
            elif isinstance(arg, basestring):
                out.writeQString(arg)
            elif type(arg) is FloatType:
                out.writeFloat(arg)
            elif type(arg) is ListType:
                out.writeQVariantList(arg)
            elif type(arg) is DictType:
                out.writeQString(json.dumps(arg))                                
            elif type(arg) is QtCore.QFile :       
                arg.open(QtCore.QIODevice.ReadOnly)
                fileDatas = QtCore.QByteArray(arg.readAll())
                #seems that that logger doesn't work
                #logger.debug("file size ", int(fileDatas.size()))
                out.writeInt(fileDatas.size())
                out.writeRawData(fileDatas)

                # This may take a while. We display the progress bar so the user get a feedback
                self.sendFile = True
                self.progress.setLabelText("Sending file to server")
                self.progress.setCancelButton(None)
                self.progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
                self.progress.setAutoClose(True)
                self.progress.setMinimum(0)
                self.progress.setMaximum(100)
                self.progress.setModal(1)
                self.progress.setWindowTitle("Uploading in progress")
 
                self.progress.show()
                arg.close()
            else:
                logger.warn("Uninterpreted Data Type: " + str(type(arg)) + " sent as str: " + str(arg))
                out.writeQString(str(arg))

        out.device().seek(0)        
        out.writeUInt32(block.size() - 4)
        self.bytesToSend = block.size() - 4
    
        self.socket.write(block)

    @QtCore.pyqtSlot(QtNetwork.QAbstractSocket.SocketError)
    def socketError(self, error):
        logger.error("TCP Socket Error: " + self.socket.errorString())
        if self.state > ClientState.NONE:   # Positive client states deserve user notification.
            QtGui.QMessageBox.critical(None, "TCP Error", "A TCP Connection Error has occurred:<br/><br/><b>" + self.socket.errorString()+"</b>", QtGui.QMessageBox.Close)        
    