#-------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
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
from galacticWar import logger, LOBBY_PORT, LOBBY_HOST 
from galaxy import Galaxy

from client import ClientState
import util
import json

from types import IntType, FloatType, ListType, DictType

FormClass, BaseClass = util.loadUiType("galacticwar/galacticwar.ui")

class LobbyWidget(FormClass, BaseClass):
    def __init__(self, client, *args, **kwargs):
        logger.debug("Lobby instantiating.")
        BaseClass.__init__(self, *args, **kwargs)
        
        self.setupUi(self)
        self.client = client
        
        self.client.galacticwarTab.layout().addWidget(self)
   
        self.galaxy = Galaxy()
   
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
                self.doLogin()                    
            
        return BaseClass.showEvent(self, event)

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

        self.send(dict(command="hello", login=self.client.login, session = self.client.session))
        
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
        from glDisplay import GLWidget
        self.OGLdisplay = GLWidget(self)
        self.galaxyTab.layout().addWidget(self.OGLdisplay)

        

    def handle_welcome(self, message):
        self.state = ClientState.ACCEPTED

    def handle_planet_info(self, message):
        uid = message['uid'] 
        if not uid in self.galaxy.control_points :
            x = message['posx']
            y = message['posy']
            size = message['size']
            self.galaxy.addPlanet(uid, x, y, size, init=True) 
            
            if not uid in self.galaxy.links :
                print message['links']
                self.galaxy.links[uid] = message['links']

    def handle_init_done(self, message):
        if message['status'] == True :
            self.galaxy.computeVoronoi()
            self.setup()
            

    def process(self, action, stream):
        #logger.debug("Server: " + action)

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
        
            #Clear the online users lists
            oldplayers = self.players.keys()
            self.players = {}
            self.urls = {}
            self.usersUpdated.emit(oldplayers)
            
            self.disconnected.emit()            
            
            self.mainTabs.setCurrentIndex(0)
            
            for i in range(1, self.mainTabs.count()):
                self.mainTabs.setTabEnabled(i, False)
                self.mainTabs.setTabText(i, "offline")
                
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
    