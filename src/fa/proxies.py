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





from PyQt4 import QtCore, QtNetwork

import functools

import logging
import json

FAF_PROXY_HOST = "direct.faforever.com"
#FAF_PROXY_HOST = "localhost"
FAF_PROXY_PORT = 9123

UNIT16 = 8

class proxies(QtCore.QObject):
    __logger = logging.getLogger("faf.fa.proxies")
    __logger.setLevel(logging.DEBUG)

    def __init__(self, parent=None):
        super(proxies, self).__init__(parent)

        self.client = parent

        self.proxies = {}
        self.proxiesDestination = {}
        port = 12000
        for i in range(11) :
            port = port + i
            self.proxies[i] = QtNetwork.QUdpSocket(self)
            if not self.proxies[i].bind(QtNetwork.QHostAddress.LocalHost, port) :
                self.__logger.warn("Can't bind socket %i" % i)
            else :
                self.__logger.info("binding socket %i on port %i" % (i, self.proxies[i].localPort()))
                self.proxies[i].readyRead.connect(functools.partial(self.processPendingDatagrams, i))
                self.proxiesDestination[i] = None

        self.proxySocket = QtNetwork.QTcpSocket(self)
        self.proxySocket.connected.connect(self.connectedProxy)
        self.proxySocket.readyRead.connect(self.readData) 
        
        self.blockSize = 0
        
    def connectedProxy(self):
        ''' Setting the socket option correctly'''
        # we want the low delay for performance.
        self.__logger.debug("Setting low delay on socket.")
        self.proxySocket.setSocketOption(QtNetwork.QAbstractSocket.LowDelayOption, 1)

    def connectToProxy(self):
        self.proxySocket.connectToHost(FAF_PROXY_HOST, FAF_PROXY_PORT)
        if self.proxySocket.waitForConnected(10000):
            self.__logger.debug("faf server " + self.proxySocket.peerName() + ":" + str(self.proxySocket.peerPort()))

    def bindSocket(self, port, address):
        self.proxiesDestination[port] = address
        if not self.proxySocket.state() == QtNetwork.QAbstractSocket.ConnectedState :
            self.connectToProxy()
        return self.proxies[port].localPort()
        
    def releaseSocket(self, port):
        self.proxiesDestination[port] = None

    def tranfertToUdp(self, port, packet):
        print "sending packet to", port
        print packet
        self.proxies[port].writeDatagram(packet, QtNetwork.QHostAddress.LocalHost, self.client.gamePort)

    def readData(self):
        if self.socket.isValid() :           
            if self.socket.bytesAvailable() == 0 :
                return
            ins = QtCore.QDataStream(self.proxySocket)
            ins.setVersion(QtCore.QDataStream.Qt_4_2)
            while ins.atEnd() == False :                             
                if self.socket.isValid() :
                    if self.blockSize == 0:
                        if self.socket.isValid() :
                            if self.socket.bytesAvailable() < 4:
                                return

                            self.blockSize = ins.readUInt32()
                        else :
                            return
        
                    if self.socket.isValid() :
                        if self.socket.bytesAvailable() < self.blockSize:
                            return

                    else :
                        return  
                    port = int(ins.readUInt8())
                    packet  = ins.readQVariant()
                    
                    self.tranfertToUdp(port, packet)
                    
                    self.blockSize = 0
      
                else : 
                    return    
            return                

    def sendReply(self, port, address, packet, *args, **kwargs) :
        reply = QtCore.QByteArray()
        stream = QtCore.QDataStream(reply, QtCore.QIODevice.WriteOnly)
        stream.setVersion(QtCore.QDataStream.Qt_4_2)
        stream.writeUInt32(0)
        

        stream.writeUInt8(str(port))
        stream.writeQString(address)
        
        stream.writeQVariant(packet)

        stream.device().seek(0)
        
        stream.writeUInt32(reply.size() - 4)

        if self.proxySocket.write(reply) == -1 :
            print "sending packet"
            print packet
            self.__logger.debug("error socket write")

    def processPendingDatagrams(self, i):
        udpSocket = self.proxies[i]
        while udpSocket.hasPendingDatagrams():
            datagram, _, _ = udpSocket.readDatagram(udpSocket.pendingDatagramSize())
            self.__logger.debug("sending data")
            print i
            print self.proxiesDestination[i]
            self.sendReply(i, self.proxiesDestination[i], datagram)

            