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
import time
#import util
import json
import logging
import fa

logger = logging.getLogger("faf.gwinfo")
logger.setLevel(logging.DEBUG)

def log(string):
    logger.debug(string)

# A set of exceptions we use to see what goes wrong during asynchronous data transfer waits
class GwInfoCancellation(StandardError):
    pass

class GwInfoFailure(StandardError):
    pass    

class GwInfoTimeout(StandardError):
    pass
    

class GWReplayInfo(QtCore.QObject):
    '''
    This class is prepared files to see the GW replay correctly.
    '''
    # Network configuration
    SOCKET  = 11002
    HOST    = "faforever.com"
    TIMEOUT = 20  #seconds

    # Return codes to expect from run()
    RESULT_SUCCESS = 0      # successful
    RESULT_NONE = -1        # operation is still ongoing
    RESULT_FAILURE = 1      # an error occured
    RESULT_CANCEL = 2       # User cancelled
    RESULT_BUSY = 4         # Server is currently busy
    RESULT_PASS = 5         # User refuses to update by canceling
    
    def __init__(self, gameid, *args, **kwargs):
        '''
        Constructor
        '''
        QtCore.QObject.__init__(self, *args, **kwargs)
        
        self.uid            = gameid
        self.infos          = None
        
        self.lastData = time.time()
        self.result = self.RESULT_NONE
        
        self.blockSize = 0
        self.gwInfoSocket = QtNetwork.QTcpSocket()
        self.gwInfoSocket.setSocketOption(QtNetwork.QTcpSocket.KeepAliveOption, 1)
        self.gwInfoSocket.setSocketOption(QtNetwork.QTcpSocket.LowDelayOption, 1)

        self.progress = QtGui.QProgressDialog()        
        self.progress.setCancelButtonText("Cancel")
        self.progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
        self.progress.setAutoClose(False)
        self.progress.setAutoReset(False)
        self.progress.setModal(1)
        self.progress.setWindowTitle("Preparing Galactic War replay %i" % self.uid)
        
    def run(self, *args, **kwargs):
        ''' actually do the settings'''
        self.progress.show()
        QtGui.QApplication.processEvents() 

        self.progress.setLabelText("Connecting to server...")
        self.gwInfoSocket.error.connect(self.handleServerError)
        self.gwInfoSocket.readyRead.connect(self.readDataFromServer)
        self.gwInfoSocket.disconnected.connect(self.disconnected)
        self.gwInfoSocket.error.connect(self.errored)
        
        self.gwInfoSocket.connectToHost(self.HOST, self.SOCKET)                         

        while not (self.gwInfoSocket.state() == QtNetwork.QAbstractSocket.ConnectedState) and self.progress.isVisible():
            QtGui.QApplication.processEvents()
                                                    
        if not self.progress.wasCanceled():
            
            self.doUpdate()        

            self.progress.setLabelText("Cleaning up.")        
            self.gwInfoSocket.close()        
            self.progress.close()                
        else:

            self.result = self.RESULT_CANCEL
        return self.result  

    def doUpdate(self):
        ''' The core function that does most of the actual work.'''
        self.send(dict(command="gw_game_info", uid=self.uid))
        self.waitForInfo()
        
    def handle_gw_game_info(self, message):
        self.infos = json.loads(message["table"])        
        fa.gwgametable.writeTable(self.infos, "gwReinforcementList.gw")
        self.result = self.RESULT_SUCCESS
        
    def waitForInfo(self):
        '''
        A simple loop that waits until the server has transmitted our info.
        '''        
        self.progress.setValue(0)
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        while self.infos == None :
            if (self.progress.wasCanceled()) : raise GwInfoCancellation("Operation aborted while waiting for info.")
            if (self.result != self.RESULT_NONE) : raise GwInfoFailure("Operation failed while waiting for info.")
            if (time.time() - self.lastData > self.TIMEOUT) : raise GwInfoTimeout("Operation timed out while waiting for info.")
            QtGui.QApplication.processEvents()
            
    def send(self, message):
        data = json.dumps(message)
        logger.debug("Outgoing JSON Message: " + data)
        self.writeToServer(data)      

    @QtCore.pyqtSlot()
    def readDataFromServer(self):
        ins = QtCore.QDataStream(self.gwInfoSocket)        
        ins.setVersion(QtCore.QDataStream.Qt_4_2)
        
        while ins.atEnd() == False :
            if self.blockSize == 0:
                if self.gwInfoSocket.bytesAvailable() < 4:
                    return
                self.blockSize = ins.readUInt32()            
            if self.gwInfoSocket.bytesAvailable() < self.blockSize:
                return
            
            action = ins.readQString()
            self.process(action, ins)
            self.blockSize = 0
            
    def writeToServer(self, action, *args, **kw):               
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
            else:
                out.writeQString(str(arg))      

        out.device().seek(0)
        out.writeUInt32(block.size() - 4)

        self.bytesToSend = block.size() - 4        
        self.gwInfoSocket.write(block)


    def process(self, action, stream):
        self.receiveJSON(action, stream)
        
    def receiveJSON(self, data_string, stream):
        '''
        A fairly pythonic way to process received strings as JSON messages.
        '''
        message = json.loads(data_string)
        cmd = "handle_" + message['command']
        if hasattr(self, cmd):
            getattr(self, cmd)(message)
       

    @QtCore.pyqtSlot('QAbstractSocket::SocketError')
    def handleServerError(self, socketError):
        '''
        Simple error handler that flags the whole operation as failed, not very graceful but what can you do...
        '''
        if socketError == QtNetwork.QAbstractSocket.RemoteHostClosedError:
            log("FA Server down: The server is down for maintenance, please try later.")

        elif socketError == QtNetwork.QAbstractSocket.HostNotFoundError:
            log("Connection to Host lost. Please check the host name and port settings.")
            
        elif socketError == QtNetwork.QAbstractSocket.ConnectionRefusedError:
            log("The connection was refused by the peer.")
        else:
            log("The following error occurred: %s." % self.gwInfoSocket.errorString())    

        self.result = self.RESULT_FAILURE  

    @QtCore.pyqtSlot()
    def disconnected(self):
        #This isn't necessarily an error so we won't change self.result here.
        pass


    @QtCore.pyqtSlot(QtNetwork.QAbstractSocket.SocketError)
    def errored(self, error):
        self.result = self.RESULT_FAILURE
      