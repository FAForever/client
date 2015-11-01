


from PyQt4 import QtCore, QtGui, QtNetwork

import functools

import logging

import config
from config import Settings

FAF_PROXY_HOST = Settings.get('HOST', 'PROXY')
FAF_PROXY_PORT = Settings.get('PORT', 'PROXY')

UNIT16 = 8


class proxies(QtCore.QObject):
    __logger = logging.getLogger(__name__)

    def __init__(self, parent=None):
        super(proxies, self).__init__(parent)

        self.client = parent

        self.proxies = {}
        self.proxiesDestination = {}
        port = 12000
        errored = False
        for i in range(11) :
            port = port + 1
            self.proxies[i] = QtNetwork.QUdpSocket(self)
            if not self.proxies[i].bind(QtNetwork.QHostAddress.LocalHost, port) :
                self.__logger.warn("Can't bind socket %i" % i)
                errored = True
            else :
                self.__logger.info("binding socket %i on port %i" % (i, self.proxies[i].localPort()))
                self.proxies[i].readyRead.connect(functools.partial(self.processPendingDatagrams, i))
                self.proxiesDestination[i] = None
        if errored:
            return None

        self.proxySocket = QtNetwork.QTcpSocket(self)
        self.proxySocket.connected.connect(self.connectedProxy)
        self.proxySocket.readyRead.connect(self.readData)
        self.proxySocket.disconnected.connect(self.disconnectedFromProxy)
        
        self.blockSize = 0
        self.uid = None
        self.canClose = False
        self.testedPortsAmount = {}
        self.testedPorts = []
        self.testedLoopbackAmount = {}
        self.testedLoopback = []
        self.testing = False
        
    def testingProxy(self):
        self.testing = True
        self.testedPortsAmount = {}
        self.testedPorts = []
        self.testedLoopbackAmount = {}
        self.testedLoopback = []
                    
    def stopTesting(self):
        self.testing = False
        self.testedPortsAmount = {}
        self.testedPorts = []
        self.testedLoopbackAmount = {}
        self.testedLoopback = []
    
    def setUid(self, uid):
        self.uid = uid

    def connectedProxy(self):
        ''' Setting the socket option correctly'''
        # we want the low delay for performance.
        self.__logger.debug("Setting low delay on socket.")
        self.proxySocket.setSocketOption(QtNetwork.QAbstractSocket.LowDelayOption, 1)

    def connectToProxy(self):
        self.proxySocket.connectToHost(FAF_PROXY_HOST, FAF_PROXY_PORT)
        if self.proxySocket.waitForConnected(10000):
            self.__logger.info("Connected to proxy server " + self.proxySocket.peerName() + ":" + str(self.proxySocket.peerPort()))
        
        self.canClose = False
        self.testedPorts = []
        self.testedLoopback = []
        self.sendUid()
            
    def bindSocket(self, port, uid):
        self.proxiesDestination[port] = uid
        self.__logger.debug("Binding socket "+ str(port) +" (local port : "+ str(self.proxies[port].localPort()) +") for uid "+ str(uid))
        if not self.proxySocket.state() == QtNetwork.QAbstractSocket.ConnectedState :
            self.connectToProxy()
        return self.proxies[port].localPort()
        
    def releaseSocket(self, port):
        self.proxiesDestination[port] = None

    def tranfertToUdp(self, port, packet):
        if self.testing:
            if not port in self.testedLoopbackAmount:
                self.testedLoopbackAmount[port] = 0
            if self.testedLoopbackAmount[port] < 10:
                self.testedLoopbackAmount[port] = self.testedLoopbackAmount[port] + 1
            else:
                if not port in self.testedLoopback:
                    self.__logger.info("Testing proxy : Received data from proxy on port %i" % self.proxies[port].localPort())
                    self.testedLoopback.append(port)
                
            if len(self.testedLoopback) == len(self.proxies):
                self.__logger.info("Testing proxy : All ports received data correctly")
                self.client.stopTesting(success=True)
                self.testing = False
        else:
            if not port in self.testedPorts:
                self.testedPorts.append(port)
                self.__logger.debug("Received data from proxy on port %i, forwarding to FA" % self.proxies[port].localPort())

            self.proxies[port].writeDatagram(packet, QtNetwork.QHostAddress.LocalHost, self.client.gamePort)

    def readData(self):
        if self.proxySocket.isValid() :           
            if self.proxySocket.bytesAvailable() == 0 :
                return
            ins = QtCore.QDataStream(self.proxySocket)
            ins.setVersion(QtCore.QDataStream.Qt_4_2)
            while ins.atEnd() == False :                             
                if self.proxySocket.isValid() :
                    if self.blockSize == 0:
                        if self.proxySocket.isValid() :
                            if self.proxySocket.bytesAvailable() < 4:
                                return

                            self.blockSize = ins.readUInt32()
                        else :
                            return
        
                    if self.proxySocket.isValid() :
                        if self.proxySocket.bytesAvailable() < self.blockSize:
                            return

                    else :
                        return  
                    port = ins.readUInt16()
                    packet  = ins.readQVariant()
                    
                    self.tranfertToUdp(port, packet)
                    
                    self.blockSize = 0
      
                else : 
                    return    
            return                

    def sendUid(self, *args, **kwargs) :
        if self.uid:
            self.__logger.warn("sending our uid (%i) to the server" % self.uid)
            reply = QtCore.QByteArray()
            stream = QtCore.QDataStream(reply, QtCore.QIODevice.WriteOnly)
            stream.setVersion(QtCore.QDataStream.Qt_4_2)
            stream.writeUInt32(0)           
                
            stream.writeUInt16(self.uid)        
            stream.device().seek(0)
            
            stream.writeUInt32(reply.size() - 4)
    
            if self.proxySocket.write(reply) == -1 :
                self.__logger.warn("error writing to proxy server !")

    def sendReply(self, port, uid, packet, *args, **kwargs) :
        reply = QtCore.QByteArray()
        stream = QtCore.QDataStream(reply, QtCore.QIODevice.WriteOnly)
        stream.setVersion(QtCore.QDataStream.Qt_4_2)
        stream.writeUInt32(0)           
            
        stream.writeUInt16(port)
        stream.writeUInt16(uid)        
        stream.writeQVariant(packet)
        stream.device().seek(0)
        
        stream.writeUInt32(reply.size() - 4)

        if self.proxySocket.write(reply) == -1 :
            self.__logger.warn("error writing to proxy server !")

    def closeSocket(self):
        if self.proxySocket.state() == QtNetwork.QAbstractSocket.ConnectedState :
            self.canClose = True
            self.__logger.info("disconnecting from proxy server")
            self.proxySocket.disconnectFromHost()
            for port in self.proxies:
                self.releaseSocket(port)
    
    def processPendingDatagrams(self, i):
        udpSocket = self.proxies[i]
        while udpSocket.hasPendingDatagrams():
            datagram, _, _ = udpSocket.readDatagram(udpSocket.pendingDatagramSize())
            if self.testing:
                if not i in self.testedPortsAmount:
                    self.testedPortsAmount[i] = 0
                    
                if self.testedPortsAmount[i] < 10:
                    self.testedPortsAmount[i] = self.testedPortsAmount[i] + 1
                else:
                    if not i in self.testedPorts:
                        self.__logger.info("Testing proxy : Received data from FA on port %i" % self.proxies[i].localPort())
                        self.testedPorts.append(i)
                        
                if len(self.testedPorts) == len(self.proxies):
                    self.__logger.info("Testing proxy : All ports triggered correctly")
                self.sendReply(i, 1, QtCore.QByteArray(datagram))
                
            else:
                if not i in self.testedLoopback:
                    self.__logger.debug("Received data from FA on port %i" % self.proxies[i].localPort())
                if self.proxiesDestination[i] != None:
                    if not i in self.testedLoopback:
                        self.testedLoopback.append(i)
                        self.__logger.debug("Forwarding packet to proxy.")
                    self.sendReply(i, self.proxiesDestination[i], QtCore.QByteArray(datagram))
                else:
                    self.__logger.warn("Unknown destination for forwarding.")

    def disconnectedFromProxy(self):
        '''Disconnection'''
        self.testedPorts = []
        self.testedLoopback = []        
        self.__logger.info("disconnected from proxy server")
        if self.canClose == False:
            self.__logger.info("reconnecting to proxy server")
            self.connectToProxy()
            
