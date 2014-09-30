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
import json
import time

INTERNET_REPLAY_SERVER_HOST = "faforever.com"
INTERNET_REPLAY_SERVER_PORT = 15000

from . import DEFAULT_LIVE_REPLAY

class ReplayRecorder(QtCore.QObject): 
    """
    This is a simple class that takes all the FA replay data input from its inputSocket, writes it to a file,
    and relays it to an internet server via its relaySocket.
    """
    __logger = logging.getLogger(__name__)
    __logger.setLevel(logging.DEBUG)
    
    def __init__(self, parent, local_socket, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.parent = parent
        self.inputSocket = local_socket
        self.inputSocket.setSocketOption(QtNetwork.QTcpSocket.KeepAliveOption, 1)
        self.inputSocket.readyRead.connect(self.readDatas)
        self.inputSocket.disconnected.connect(self.inputDisconnected)
        self.__logger.info("FA connected locally.")  
        
              
        #Create a file to write the replay data into
        self.replayData = QtCore.QByteArray()
        self.replayInfo = fa.instance.info
                 
        # Open the relay socket to our server
        self.relaySocket = QtNetwork.QTcpSocket(self.parent)
        self.relaySocket.connectToHost(INTERNET_REPLAY_SERVER_HOST, INTERNET_REPLAY_SERVER_PORT)
        
        if settings.value("fa.live_replay", DEFAULT_LIVE_REPLAY, type=bool):
            if self.relaySocket.waitForConnected(1000): #Maybe make this asynchronous
                self.__logger.debug("internet replay server " + self.relaySocket.peerName() + ":" + str(self.relaySocket.peerPort()))
            else:
                self.__logger.error("no connection to internet replay server")

        
        
    def __del__(self):
        # Clean up our socket objects, in accordance to the hint from the Qt docs (recommended practice)
        self.__logger.debug("destructor entered")
        self.inputSocket.deleteLater()
        self.relaySocket.deleteLater()
           
                 
    def readDatas(self):        
        read = self.inputSocket.read(self.inputSocket.bytesAvailable()) #CAVEAT: readAll() was seemingly truncating data here
        
        if not isinstance(read, basestring):
            self.__logger.warning("Read failure on inputSocket: " + str(bytes))
            return
        
        #Convert data into a bytearray for easier processing
        datas = QtCore.QByteArray(read)
        
        # Record locally
        if self.replayData.isEmpty():
            #This prefix means "P"osting replay in the livereplay protocol of FA, this needs to be stripped from the local file            
            if datas.startsWith("P/"):    
                rest = datas.indexOf("\x00") + 1
                self.__logger.info("Stripping prefix '" + str(datas.left(rest)) + "' from replay.")
                self.replayData.append(datas.right(datas.size() - rest))
            else:
                self.replayData.append(datas)                
        else:
            #Write to buffer
            self.replayData.append(datas)

        # Relay to faforever.com
        if self.relaySocket.isOpen():
            self.relaySocket.write(datas)
        


    def done(self):
        self.__logger.info("closing replay file")
        self.parent.removeRecorder(self)


    @QtCore.pyqtSlot()
    def inputDisconnected(self):
        self.__logger.info("FA disconnected locally.")
        
        # Part of the hardening - ensure all buffered local replay data is read and relayed
        if self.inputSocket.bytesAvailable():
            self.__logger.info("Relaying remaining bytes:" + str(self.inputSocket.bytesAvailable()))
            self.readDatas()
            
        # Part of the hardening - ensure successful sending of the rest of the replay to the server
        if self.relaySocket.bytesToWrite():
            self.__logger.info("Waiting for replay transmission to finish: " + str(self.relaySocket.bytesToWrite()) + " bytes")

            progress = QtGui.QProgressDialog("Finishing Replay Transmission", "Cancel", 0, 0)
            progress.show()

            while self.relaySocket.bytesToWrite() and progress.isVisible():
                QtGui.QApplication.processEvents()

            progress.close()

        self.relaySocket.disconnectFromHost()
        
        self.writeReplayFile()
        
        self.done()


    def writeReplayFile(self):
        # Update info block if possible.
        if fa.instance.info and fa.instance.info['uid'] == self.replayInfo['uid']:
            if fa.instance.info.setdefault('complete', False):
                self.__logger.info("Found Complete Replay Info")
            else:
                self.__logger.warn("Replay Info not Complete")
            
            self.replayInfo = fa.instance.info
                 
        self.replayInfo['game_end'] = time.time()
        
        filename = os.path.join(util.REPLAY_DIR, str(self.replayInfo['uid']) + "-" + self.replayInfo['recorder'] + ".fafreplay")
        self.__logger.info("Writing local replay as " + filename + ", containing " + str(self.replayData.size()) + " bytes of replay data.")
               
        replay  = QtCore.QFile(filename)
        replay.open(QtCore.QIODevice.WriteOnly | QtCore.QIODevice.Text)
        replay.write(json.dumps(self.replayInfo))
        replay.write('\n')
        replay.write(QtCore.qCompress(self.replayData).toBase64())
        replay.close()
        

class ReplayServer(QtNetwork.QTcpServer):
    """
    This is a local listening server that FA can send its replay data to.
    It will instantiate a fresh ReplayRecorder for each FA instance that launches.
    """
    __logger = logging.getLogger(__name__)
    __logger.setLevel(logging.INFO)

    def __init__(self, client, *args, **kwargs):
        QtNetwork.QTcpServer.__init__(self, *args, **kwargs)
        self.recorders = []
        self.client = client                
        self.__logger.debug("initializing...")
        self.newConnection.connect(self.acceptConnection)
        
        
    def doListen(self,local_port):
        while not self.isListening():
            self.listen(QtNetwork.QHostAddress.LocalHost, local_port)
            if self.isListening():
                self.__logger.info("listening on address " + self.serverAddress().toString() + ":" + str(self.serverPort()))
            else:
                self.__logger.error("cannot listen, port probably used by another application: " + str(local_port))
                answer = QtGui.QMessageBox.warning(None, "Port Occupied", "FAF couldn't start its local replay server, which is needed to play Forged Alliance online. Possible reasons:<ul><li><b>FAF is already running</b> (most likely)</li><li>another program is listening on port {port}</li></ul>".format(port=local_port), QtGui.QMessageBox.Retry, QtGui.QMessageBox.Abort)
                if answer == QtGui.QMessageBox.Abort:
                    return False
        return True
              
              
    def removeRecorder(self, recorder):
        if recorder in self.recorders:
            self.recorders.remove(recorder)
            
            
    @QtCore.pyqtSlot()       
    def acceptConnection(self):
        socket = self.nextPendingConnection()
        self.__logger.debug("incoming connection...")
        self.recorders.append(ReplayRecorder(self, socket))
        pass

