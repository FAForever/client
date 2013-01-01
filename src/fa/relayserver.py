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

import os
import logging
import util
import fa
import time
import json

import struct


FAF_SERVER_HOST = "faforever.com"
#FAF_SERVER_HOST = "localhost"
FAF_SERVER_PORT = 7001



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

class UDPRelayer(QtCore.QObject): 
    '''
    This is a simple class that takes all the UDP FA data 
    and send them to a distant client.
    '''
    __logger = logging.getLogger("faf.fa.udprelayer")
    __logger.setLevel(logging.DEBUG)
    
    def __init__(self, parent, host, port, localport = None, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.parent = parent       
        
        self.host = host
        self.port = port
        self.foreignAddress  =  host.toString() + ":" + str(port)
        
        self.udpSocket =  QtNetwork.QUdpSocket(self)

        if localport == None :
            self.udpSocket.bind(QtNetwork.QHostAddress.LocalHost, 0)
        else :
            self.udpSocket.bind(QtNetwork.QHostAddress.LocalHost, localport)
        self.localPort = self.udpSocket.localPort()
        self.udpSocket.readyRead.connect(self.processPendingDatam)          
        
        self.__logger.info("External address %s mapped to local port %i" % (self.foreignAddress, self.localPort))
        
    def getLocalPort(self):
        return self.localPort
    
    def close(self):
        self.udpSocket.close()
        #self.udpSocket.deleteLater()
    
    def processPendingDatam(self):
        # we receive datas from FA

        while self.udpSocket.hasPendingDatagrams():
            datagram, host, port = self.udpSocket.readDatagram(self.udpSocket.pendingDatagramSize())
            #we now have to relay them to the correct client !
            self.parent.udpSocket.writeDatagram(datagram, self.host, self.port)

    def write(self, datagram) :

        
        self.udpSocket.writeDatagram(datagram, QtNetwork.QHostAddress.LocalHost, self.parent.faport)
        
    

class Relayer(QtCore.QObject): 
    '''
    This is a simple class that takes all the FA data input from its inputSocket 
    and relays it to an internet server via its relaySocket.
    '''
    __logger = logging.getLogger("faf.fa.relayer")
    __logger.setLevel(logging.DEBUG)
    
    def __init__(self, parent, client, local_socket, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.parent = parent
        self.inputSocket = local_socket
        self.client = client
        
        self.faport = 0
        #generate a random FA port
        fasocket = QtNetwork.QUdpSocket(self)
        fasocket.bind(0)
        self.faport = fasocket.localPort()
        fasocket.close()
        fasocket.deleteLater()
        
        self.knownUdpClients = {}
        
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

        #self.inputSocket.setSocketOption(QtNetwork.QTcpSocket.KeepAliveOption, 1)
        self.inputSocket.readyRead.connect(self.readDatas)
        self.inputSocket.disconnected.connect(self.inputDisconnected)
        self.__logger.info("FA connected locally.")  
        
        
#        self.udpSocket =  QtNetwork.QUdpSocket(self)
#        self.udpSocket.bind(self.client.gamePort)

        self.__logger.info("FA will use local port %i", self.faport)  
        self.__logger.info("UDP relay port %i", self.client.gamePort)
        
#        self.udpSocket.readyRead.connect(self.processPendingDatam)

        # Open the relay socket to our server
        self.relaySocket = QtNetwork.QTcpSocket(self.parent)        
        #self.relaySocket .setSocketOption(QtNetwork.QTcpSocket.KeepAliveOption, 1)
        self.relaySocket.connectToHost(FAF_SERVER_HOST, FAF_SERVER_PORT)        
        
        if self.relaySocket.waitForConnected(10000): #Maybe make this asynchronous
            self.__logger.debug("faf server " + self.relaySocket.peerName() + ":" + str(self.relaySocket.peerPort()))  
        else:
            self.__logger.error("no connection to internet relay server")

        self.relaySocket.readyRead.connect(self.readDatasFromServer)
        
    def __del__(self):
        #Find out whether this really does what it should (according to docs, sockets should be manually deleted to conserver resources)
        self.inputSocket.deleteLater()
        self.relaySocket.deleteLater()
        self.__logger.debug("destructor called")        
           
           
    def processPendingDatam(self):
        while self.udpSocket.hasPendingDatagrams():
            datagram, host, port = self.udpSocket.readDatagram(self.udpSocket.pendingDatagramSize())
            address = host.toString() + ":" + str(port)
            socket = None
            if not address in self.knownUdpClients :
                #we receive datas from an unknown client

                for oldaddress in self.knownUdpClients :
                    if self.knownUdpClients[oldaddress].host == host :
                        #it's probably our guy.

                        
                        oldPort = self.knownUdpClients[oldaddress].getLocalPort()
                        self.knownUdpClients[oldaddress].close()
                        socket = UDPRelayer(self, QtNetwork.QHostAddress(host), port, oldPort)
                        self.knownUdpClients[address] = socket
                        
                        break
            
                if socket == None :
                    socket = UDPRelayer(self, QtNetwork.QHostAddress(host), port)
                    self.knownUdpClients[address] = socket
                    

            else :
                socket = self.knownUdpClients[address]
            
            if socket != None :
                socket.write(datagram)
            else :
                self.__logger.debug("no socket found") 
                


    def readDatasFromServer(self):
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



    def readDatas(self):
        self.__logger.info("reading socket from FA") 
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
      
                self.sendToServer(self.action, self.chunks)
                self.action = None
                self.chunks = []
                self.headerSizeRead = False
                self.headerRead = False
                self.chunkSizeRead = False
                self.fieldTypeRead = False
                self.fieldSizeRead = False
                

                
    def sendToServer(self, action, chunks):
        # Relay to faforever.com
        if self.relaySocket.isOpen():
            data = json.dumps(dict(action=action, chuncks=chunks))
            self.__logger.info("Command received from FA : " + data)
            
            block = QtCore.QByteArray()
            out = QtCore.QDataStream(block, QtCore.QIODevice.ReadWrite)
            out.setVersion(QtCore.QDataStream.Qt_4_2)
            out.writeUInt32(0)
            out.writeQString(data)
            out.device().seek(0)        
            out.writeUInt32(block.size() - 4)
            self.bytesToSend = block.size() - 4
            self.relaySocket.writeData(block)

    def handleAction(self, commands):    
        key = commands["key"]
        acts = commands["commands"]
  
        if key == "SendNatPacket" :
            reply = Packet(key, acts)
            self.inputSocket.write(reply.PackUdp())
        else :

            reply = Packet(key, acts)
            self.inputSocket.write(reply.Pack())


    def done(self):
        self.__logger.info("remove relay")
        self.parent.removeRelay(self)


    @QtCore.pyqtSlot()
    def inputDisconnected(self):
        self.__logger.info("FA disconnected locally.")
       
        self.relaySocket.disconnectFromHost()
        self.done()



class RelayServer(QtNetwork.QTcpServer):
    ''' 
    This is a local listening server that FA can send its replay data to.
    It will instantiate a fresh ReplayRecorder for each FA instance that launches.
    '''
    __logger = logging.getLogger("faf.fa.relayserver")
    __logger.setLevel(logging.DEBUG)

    def __init__(self, client, *args, **kwargs):
        QtNetwork.QTcpServer.__init__(self, *args, **kwargs)
        self.relayers = []
        self.client = client
      
        self.__logger.debug("initializing...")
        self.newConnection.connect(self.acceptConnection)
        
        
    def doListen(self):
        while not self.isListening():
            self.listen(QtNetwork.QHostAddress.LocalHost, 0)
            if (self.isListening()):
                self.__logger.info("relay listening on address " + self.serverAddress().toString() + ":" + str(self.serverPort()))
            else:
                self.__logger.error("cannot listen, port probably used by another application: " + str(local_port))
                answer = QtGui.QMessageBox.warning(None, "Port Occupied", "FAF couldn't start its local relay server, which is needed to play Forged Alliance online. Possible reasons:<ul><li><b>FAF is already running</b> (most likely)</li><li>another program is listening on port {port}</li></ul>".format(port=local_port), QtGui.QMessageBox.Retry, QtGui.QMessageBox.Abort)
                if answer == QtGui.QMessageBox.Abort:
                    return False
        return True
              
    def removeRelay(self, relay):
#        if relay in self.relayers:
#            relay.udpSocket.close()
#            relay.udpSocket.deleteLater()
#            
#            for socket in relay.knownUdpClients :
#                relay.knownUdpClients[socket].udpSocket.close()
#                relay.knownUdpClients[socket].udpSocket.deleteLater()
            
            self.relayers.remove(relay)
            
            
    @QtCore.pyqtSlot()       
    def acceptConnection(self):
        socket = self.nextPendingConnection()
        self.__logger.debug("incoming connection to relay server...")
        self.relayers.append(Relayer(self, self.client, socket))
        pass

