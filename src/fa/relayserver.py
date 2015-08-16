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


from PyQt4 import QtCore, QtNetwork, QtGui

import logging
import json
from config import Settings

import struct

FAF_SERVER_HOST = Settings.get('HOST', 'RELAY_SERVER')
FAF_SERVER_PORT = Settings.get('PORT', 'RELAY_SERVER')


class Packet():
    def __init__(self, header=None , data=None, *values, **kwvalues):
        
        self._data = data  
        self._values = kwvalues
        self._header = header
    
    def Pack(self):

        data = ""
        
        headerSize = len(str(self._header))
        headerField = str(self._header).replace("\t","/t").replace("\n","/n")
        chunkSize = len(self._data)
        headerPackStr = "<i" + str(headerSize) + "si"
        data += struct.pack(headerPackStr, headerSize, headerField, chunkSize)

        for field in self._data :      
            fieldType = 0 if type(field) is int else 1

            chunkPackStr = ""
            fields = []
            if fieldType is 1:
                fieldSize = len(field)
                chunkPackStr += "<bi" + str(fieldSize) + "s"
                fieldStr = str(field).replace("\t","/t").replace("\n","/n")
                fields.extend([fieldType, fieldSize, fieldStr])
            elif fieldType is 0:
                chunkPackStr += "<bi"
                fields.extend([fieldType, field])
            data += struct.pack(chunkPackStr, *fields)

        return data
    
    def PackUdp(self):

        data = ""
        headerSize = len(str(self._header))
        headerField = str(self._header).replace("\t","/t").replace("\n","/n")
        chunkSize = len(self._data)
        headerPackStr = "<i" + str(headerSize) + "si"
        data += struct.pack(headerPackStr, headerSize, headerField, chunkSize)
        i = 0
        for field in self._data :
                fieldType = 0 if type(field) is int else 1

                chunkPackStr = ""
                fields = []
                if fieldType is 1:

                    datas = "\x08"
                    if i == 1 :
                        fieldSize = len(field) + len(datas)
                    else :
                        fieldSize = len(field)
                        
                    chunkPackStr += "<bi" + str(fieldSize) + "s"
                    fieldStr = str(field).replace("\t","/t").replace("\n","/n")
                    if i == 1 :
                        fields.extend([2, fieldSize, datas+fieldStr])
                    else :
                        fields.extend([fieldType, fieldSize, fieldStr])
                elif fieldType is 0:
                    chunkPackStr += "<bi"
                    fields.extend([fieldType, field])
                data += struct.pack(chunkPackStr, *fields)
                i = 1
        return data


class Relayer(QtCore.QObject): 
    '''
    This is a simple class that takes all the FA data input from its inputSocket 
    and relays it to an internet server via its relaySocket.
    '''
    __logger = logging.getLogger(__name__)

    def __init__(self, parent, client, local_socket, testing, init_mode=1, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)

        self.parent = parent
        self.inputSocket = local_socket
        self.client = client
        self.testing = testing

        # for unpacking FA protocol
        self.blockSizeFromServer = 0
        self.headerSizeRead = False
        self.headerRead = False
        self.chunkSizeRead = False
        self.fieldTypeRead = False
        self.fieldSizeRead = False
        self.blockSize = 0
        self.fieldSize = 0
        self.chunkSize = 0
        self.fieldType = 0
        self.chunks = []

        self.pingTimer = None
        self.init_mode = init_mode

        #self.inputSocket.setSocketOption(QtNetwork.QTcpSocket.KeepAliveOption, 1)
        self.inputSocket.readyRead.connect(self.readData)
        self.inputSocket.disconnected.connect(self.inputDisconnected)
        self.__logger.info("FA connected locally.")  
        

        # Open the relay socket to our server
        self.relaySocket = QtNetwork.QTcpSocket(self.parent)        
        self.relaySocket.setSocketOption(QtNetwork.QTcpSocket.KeepAliveOption, 1)
        self.relaySocket.connectToHost(FAF_SERVER_HOST, FAF_SERVER_PORT)
        self.relaySocket.connected.connect(self.on_connected)
        self.relaySocket.error.connect(self.on_error)

    def on_error(self, socketError):
        self.__logger.error(self.relaySocket.errorString())

    def on_connected(self):
        self.__logger.debug("faf server " + self.relaySocket.peerName() + ":" + str(self.relaySocket.peerPort()))
        self.__logger.debug("Initializing ping timer")
        self.pingTimer = QtCore.QTimer(self)
        self.pingTimer.timeout.connect(self.ping)
        self.pingTimer.start(30000)
        self.sendToServer('Authenticate', [self.client.session, self.client.id])
        self.relaySocket.readyRead.connect(self.readDataFromServer)

    def __del__(self):
        #Find out whether this really does what it should (according to docs, sockets should be manually deleted to conserver resources)
        self.inputSocket.deleteLater()
        self.relaySocket.deleteLater()
        self.__logger.debug("destructor called")        
           
    def readDataFromServer(self):
        ins = QtCore.QDataStream(self.relaySocket)        
        ins.setVersion(QtCore.QDataStream.Qt_4_2)
        
        while ins.atEnd() == False :
            if self.blockSizeFromServer == 0:
                if self.relaySocket.bytesAvailable() < 4:
                    return
                self.blockSizeFromServer = ins.readUInt32()            
            if self.relaySocket.bytesAvailable() < self.blockSizeFromServer:
                return

            commands = ins.readQString()
            self.__logger.info("Command received from server : " + commands)
            self.handleAction(json.loads(commands))
            self.blockSizeFromServer = 0



    def readData(self):
        if self.inputSocket.bytesAvailable() == 0 :
            self.__logger.info("data reception read done - too or not enough data")
            return
        
        ins = QtCore.QDataStream(self.inputSocket)
        ins.setByteOrder(QtCore.QDataStream.LittleEndian)  

        while ins.atEnd() == False :
            if self.inputSocket.isValid() :
                if self.headerSizeRead == False :
                    if self.inputSocket.bytesAvailable() < 4:
                        return
                
                    self.blockSize = ins.readUInt32()
                    self.headerSizeRead = True
                    
                if self.headerRead == False :
                
                    if self.inputSocket.bytesAvailable() < self.blockSize :
                        return
                
                    self.action = ins.readRawData(self.blockSize)
                    self.headerRead = True
                    
                if self.chunkSizeRead == False :
                    if self.inputSocket.bytesAvailable() < 4:
                        return
                
                    self.chunkSize = ins.readInt32()
                    self.chunks = []
                    self.chunkSizeRead = True
                
                if self.chunkSize > 100 :
                    self.__logger.info("Big error reading FA datas !")
                    self.inputSocket.readAll()
                    self.fieldSize = 0
                    self.blockSize = 0
                    self.chunkSize = 0  
                    self.noSocket = True                         
                    return
                
                for _ in range(len(self.chunks), self.chunkSize):
                    if self.fieldTypeRead == False :
                        if self.inputSocket.bytesAvailable() < 1 :
                            return
                                
                        self.fieldType = ins.readBool()
                        self.fieldTypeRead = True
                    
                    if not self.fieldType :
                     
                        if self.inputSocket.bytesAvailable() < 4 :
                            return
                        number = ins.readInt32()
                        self.chunks.append(number)
                        self.fieldTypeRead = False         

                    else :
                        if self.fieldSizeRead == False :      
                            if self.inputSocket.bytesAvailable() < 4 :
                                return  
                              
                            self.fieldSize =  ins.readInt32()
                            self.fieldSizeRead = True
                
                        if self.inputSocket.bytesAvailable() < self.fieldSize :
                            return

                        datastring = ins.readRawData(self.fieldSize)
                        fixedStr = datastring.replace("/t","\t").replace("/n","\n")
                        self.chunks.append(fixedStr)               
                        self.fieldTypeRead = False
                        self.fieldSizeRead = False  
      
                if not self.testing:
                    self.handle_incoming_local(self.action, self.chunks)
                else:
                    self.sendToLocal(self.action, self.chunks)
                self.action = None
                self.chunks = []
                self.headerSizeRead = False
                self.headerRead = False
                self.chunkSizeRead = False
                self.fieldTypeRead = False
                self.fieldSizeRead = False

    def handle_incoming_local(self, action, chunks):
        if self.action == 'GameState':
            if chunks[0] == 'Idle':
                self.__logger.info("Telling game to create lobby")
                reply = Packet("CreateLobby", [self.init_mode,
                                               self.client.gamePort,
                                               self.client.login,
                                               self.client.id,
                                               1])
                self.inputSocket.write(reply.Pack())
        self.sendToServer(action, chunks)

    def ping(self):
        self.sendToServer("ping", [])

    def sendToLocal(self, action, chunks):
        if action == 'GameState':
            if chunks[0] == 'Idle':
                self.client.proxyServer.setUid(1)
                reply = Packet("CreateLobby", [0, 0, "FAF Local Mode", 0, 1])
                self.inputSocket.write(reply.Pack())

            elif chunks[0] == 'Lobby':
                reply = Packet("HostGame", ["SCMP_007"])
                self.inputSocket.write(reply.Pack())
                if self.testing == True:
                    self.client.proxyServer.testingProxy()
                    for i in range(len(self.client.proxyServer.proxies)):
                        udpport = self.client.proxyServer.bindSocket(i, 1)
                        self.__logger.info("Asking to send data on proxy port %i" % udpport)
                        acts = [("127.0.0.1:%i" % udpport), "port %i" % udpport, udpport]
                        reply = Packet("ConnectToPeer", acts)
                        self.inputSocket.write(reply.Pack())
                else:
                    self.client.proxyServer.stopTesting()                    

                            
    def sendToServer(self, action, chunks):
        data = json.dumps(dict(action=action, chunks=chunks))
        # Relay to faforever.com
        if self.relaySocket.isOpen():
            if action != "ping" and action != "pong" :
                self.__logger.info("Command transmitted from FA to server : " + data)
            
            block = QtCore.QByteArray()
            out = QtCore.QDataStream(block, QtCore.QIODevice.ReadWrite)
            out.setVersion(QtCore.QDataStream.Qt_4_2)
            out.writeUInt32(0)
            out.writeQString(data)
            out.device().seek(0)        
            out.writeUInt32(block.size() - 4)
            self.bytesToSend = block.size() - 4
            self.relaySocket.writeData(block)
        else :
            self.__logger.warn("Error transmitting datas to server : " + data)

    def handleAction(self, commands):    
        key = commands["key"]
        acts = commands["commands"]
        
        if key == "ping" :
            self.sendToServer("pong", [])
            
        elif key == "SendNatPacket" :
            reply = Packet(key, acts)
            self.inputSocket.write(reply.PackUdp())

        elif key == "CreateLobby":
            uid = int(acts[3])     
            self.client.proxyServer.setUid(uid)
            self.__logger.info("Setting uid : " + str(uid))

        elif key == "ConnectToProxy" :
                port = acts[0]
                login   = acts[2]
                uid     = acts[3]
                udpport = self.client.proxyServer.bindSocket(port, uid)
                
                newActs = [("127.0.0.1:%i" % udpport), login, uid]
                
                reply = Packet("ConnectToPeer", newActs)
                self.inputSocket.write(reply.Pack())
                
        elif key == "JoinProxy" :
            port = acts[0]
            login   = acts[2]
            uid     = acts[3]
            udpport = self.client.proxyServer.bindSocket(port, uid)
            
            newActs = [("127.0.0.1:%i" % udpport), login, uid]
            
            reply = Packet("JoinGame", newActs)
            self.inputSocket.write(reply.Pack())                
            
        else :
            reply = Packet(key, acts)
            self.inputSocket.write(reply.Pack())


    def done(self):
        self.__logger.info("remove relay")
        self.parent.removeRelay(self)


    @QtCore.pyqtSlot()
    def inputDisconnected(self):
        self.__logger.info("FA disconnected locally.")
        self.client.proxyServer.closeSocket()
        self.relaySocket.disconnectFromHost()
        if self.pingTimer :
            self.pingTimer.stop()
        self.done()
        
        



class RelayServer(QtNetwork.QTcpServer):
    ''' 
    This is a local listening server that FA can send its data to.
    It will instantiate a fresh ReplayRecorder for each FA instance that launches.
    '''
    __logger = logging.getLogger(__name__)

    def __init__(self, client, *args, **kwargs):
        QtNetwork.QTcpServer.__init__(self, *args, **kwargs)
        self.relayers = []
        self.client = client
        self.local = False
        self.testing = False
        # Use normal lobby by default
        self.init_mode = 1

        self.__logger.debug("initializing...")
        self.newConnection.connect(self.acceptConnection)

    def stopTesting(self):
        self.local = False
        self.testing = False
        for relay in self.relayers:
            relay.testing = False


    def testingProxy(self):
        ''' this method is to test that everything is fine'''
        self.local = True
        self.testing = True
        for relay in self.relayers:
            relay.testing = True

        
    def doListen(self):
        while not self.isListening():
            self.listen(QtNetwork.QHostAddress.LocalHost, 0)
            if (self.isListening()):
                self.__logger.info("relay listening on address " + self.serverAddress().toString() + ":" + str(self.serverPort()))
            else:
                self.__logger.error("cannot listen, port probably used by another application: " + str(self.serverPort()))
                answer = QtGui.QMessageBox.warning(None, "Port Occupied", "FAF couldn't start its local relay server, which is needed to play Forged Alliance online. Possible reasons:<ul><li><b>FAF is already running</b> (most likely)</li><li>another program is listening on port {port}</li></ul>".format(port=str(self.serverPort())), QtGui.QMessageBox.Retry, QtGui.QMessageBox.Abort)
                if answer == QtGui.QMessageBox.Abort:
                    return False
        return True
              
    def removeRelay(self, relay):
        self.relayers.remove(relay)
            
            
    @QtCore.pyqtSlot()       
    def acceptConnection(self):
        socket = self.nextPendingConnection()
        self.__logger.debug("incoming connection to relay server...")
        self.relayers.append(Relayer(self, self.client, socket, self.testing, init_mode=self.init_mode))

