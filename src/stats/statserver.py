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

logger = logging.getLogger("faf.statserver")
logger.setLevel(logging.INFO)

def log(string):
    logger.debug(string)

# A set of exceptions we use to see what goes wrong during asynchronous data transfer waits
class Cancellation(StandardError):
    pass

class Failure(StandardError):
    pass    

class Timeout(StandardError):
    pass
    

class StatServer(QtCore.QObject):
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
    
    def __init__(self, requester, *args, **kwargs):
        '''
        Constructor
        '''
        QtCore.QObject.__init__(self, *args, **kwargs)
        
        self.requester      = requester

        self.result = self.RESULT_NONE
        self.command = None
        self.message = None
        
        self.blockSize = 0
        self.statServerSocket = QtNetwork.QTcpSocket()

        self.statServerSocket.error.connect(self.handleServerError)
        self.statServerSocket.readyRead.connect(self.readDataFromServer)
        self.statServerSocket.disconnected.connect(self.disconnected)
        self.statServerSocket.error.connect(self.errored)
        

        
    def send(self, command, *args, **kwargs):
        ''' actually do the settings'''
                  
        
        self.result = self.RESULT_NONE
        self.command = None
        self.message = None
        
        self.progress = QtGui.QProgressDialog()        
        self.progress.setCancelButtonText("Cancel")
        self.progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
        self.progress.setAutoClose(False)
        self.progress.setAutoReset(True)
        self.progress.setModal(1)
        self.progress.setWindowTitle("Connecting to statistic server")
                
        self.progress.show()        
        self.lastData = time.time()
        self.progress.setLabelText("Connecting to server...")

        self.statServerSocket.connectToHost(self.HOST, self.SOCKET)                         

        while not (self.statServerSocket.state() == QtNetwork.QAbstractSocket.ConnectedState) and self.progress.isVisible():
            QtGui.QApplication.processEvents()
        
                                     
        if not self.progress.wasCanceled():
            self.doCommand(command)        
            self.progress.setLabelText("Cleaning up.")                
            self.progress.close()                
        else:
            self.result = self.RESULT_CANCEL
        
        return self.result  

    def doCommand(self, command):
        ''' The core function that does most of the actual work.'''
        self.sendJson(command)
        self.waitForInfo()
              
    def waitForInfo(self):
        '''
        A simple loop that waits until the server has transmitted our info.
        '''        
        self.progress.setValue(0)
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        while self.result == self.RESULT_NONE :
            if (self.progress.wasCanceled()) : raise Cancellation("Operation aborted while waiting for info.")
            if (time.time() - self.lastData > self.TIMEOUT) : raise Timeout("Operation timed out while waiting for info.")
            QtGui.QApplication.processEvents()
        logger.debug("Finishing request")
        self.result = self.RESULT_NONE
        
        if self.command != None and self.message != None:
            getattr(self.requester, self.command)(self.message)
            
    def sendJson(self, message):
        data = json.dumps(message)
        logger.debug("Outgoing JSON Message: " + data)
        self.writeToServer(data)      

    @QtCore.pyqtSlot()
    def readDataFromServer(self):
        ins = QtCore.QDataStream(self.statServerSocket)        
        ins.setVersion(QtCore.QDataStream.Qt_4_2)
        
        while ins.atEnd() == False :
            if self.blockSize == 0:
                if self.statServerSocket.bytesAvailable() < 4:
                    return
                self.blockSize = ins.readUInt32()            
            if self.statServerSocket.bytesAvailable() < self.blockSize:
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
        self.statServerSocket.write(block)


    def process(self, action, stream):
        self.receiveJSON(action, stream)
        
    def receiveJSON(self, data_string, stream):
        '''
        A fairly pythonic way to process received strings as JSON messages.
        '''
        message = json.loads(data_string)
        cmd = "handle_" + message['command']
        logger.debug("answering from server :" + str(cmd))
        if hasattr(self.requester, cmd):
            self.command = cmd
            self.message = message
        
        self.statServerSocket.abort()        
        self.result = self.RESULT_SUCCESS
            
        
        

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
            log("The following error occurred: %s." % self.statServerSocket.errorString())    

        self.result = self.RESULT_FAILURE  

    @QtCore.pyqtSlot()
    def disconnected(self):
        #This isn't necessarily an error so we won't change self.result here.
        pass


    @QtCore.pyqtSlot(QtNetwork.QAbstractSocket.SocketError)
    def errored(self, error):
        self.result = self.RESULT_FAILURE
