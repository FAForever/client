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





from PyQt4 import QtCore, QtGui, QtNetwork
import util

from tourneys import logger
from tourneys.swisstourneyitem import SwissTourneyItem, SwissTourneyItemDelegate
from tourneys.hosttourneywidget import HostTourneyWidget

import json

FormClass, BaseClass = util.loadUiType("tournaments/tournaments.ui")


class TournamentsWidget(FormClass, BaseClass):
    ''' list and manage the main tournament lister '''
    SOCKET  = 11001
    HOST    = "faforever.com"
 
    
    def __init__(self, client, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)        
        
        self.setupUi(self)

        self.client = client
        self.client.tourneyTab.layout().addWidget(self)
        
        #Dictionary containing our actual tournaments.
        self.tourneys = {}
               
        self.updateTimer = QtCore.QTimer(self)
        self.updateTimer.timeout.connect(self.updateTournaments)
        self.updateTimer.start(600000)


       
        self.blockSize = 0
        self.tournamentSocket = QtNetwork.QTcpSocket()
        self.tournamentSocket.setSocketOption(QtNetwork.QTcpSocket.KeepAliveOption, 1)
        self.tournamentSocket.connectToHost(self.HOST, self.SOCKET)
        
        self.tournamentSocket.error.connect(self.handleServerError)
        self.tournamentSocket.readyRead.connect(self.readDataFromServer)
        self.tournamentSocket.disconnected.connect(self.disconnected)
        self.tournamentSocket.error.connect(self.errored)        
        
        
        self.tourneyList.setItemDelegate(SwissTourneyItemDelegate(self))
        
        self.tourneyList.itemDoubleClicked.connect(self.tourneyDoubleClicked)
        
        self.tourneysTab = {}

        #Special stylesheet for brackets
        self.stylesheet              = util.readstylesheet("tournaments/formatters/style.css")

    
    def showEvent(self, event):
        self.updateTournaments()
        return BaseClass.showEvent(self, event)

    def updateTournaments(self):
        if self.client.state == 1 : 
            if self.tournamentSocket.state() != QtNetwork.QAbstractSocket.ConnectedState:
                self.tournamentSocket.connectToHost(self.HOST, self.SOCKET)
            
            self.send(dict(command="get_tournaments"))
        
       
    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def tourneyDoubleClicked(self, item):
        '''
        Slot that attempts to join or leave a tournament.
        ''' 
        if not self.client.login in item.playersname :
            reply = QtGui.QMessageBox.question(self.client, "Register",
                "Do you want to register to this tournament ?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                self.send(dict(command="add_participant", uid=item.uid, login=self.client.login))
                self.updateTournaments()
        else :
            reply = QtGui.QMessageBox.question(self.client, "Register",
                "Do you want to leave this tournament ?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:   
                self.send(dict(command="remove_participant", uid=item.uid, login=self.client.login)) 
                self.updateTournaments()       
                

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def hostTourneyClicked(self, item):
        '''
        Hosting a tournament event
        '''
          
        hosttourneywidget = HostTourneyWidget(self, item)
        
        if hosttourneywidget.exec_() == 1 :
            if self.title != "":
                self.client.send(dict(command="create_tournament", type = item.tourney, name=self.title, min_players = self.minplayers, max_players = self.maxplayers, min_rating = self.minrating, max_rating = self.maxrating, description = self.description, date = self.date))

    def command_ping(self, message):
        self.send(dict(command="pong"))
    
    def command_tournaments_info(self, message):
        #self.tourneyList.clear()
        tournaments = message["data"]
        for uid in tournaments :
            if not uid in self.tourneys :
                self.tourneys[uid] = SwissTourneyItem(self, uid)
                self.tourneyList.addItem(self.tourneys[uid])
                self.tourneys[uid].update(tournaments[uid], self.client)
            else :
                self.tourneys[uid].update(tournaments[uid], self.client)

    def send(self, message):
        data = json.dumps(message)
        logger.debug("Outgoing JSON Message: " + data)
        self.writeToServer(data)

    @QtCore.pyqtSlot()
    def readDataFromServer(self):
        ins = QtCore.QDataStream(self.tournamentSocket)        
        ins.setVersion(QtCore.QDataStream.Qt_4_2)
        
        while ins.atEnd() == False :
            if self.blockSize == 0:
                if self.tournamentSocket.bytesAvailable() < 4:
                    return
                self.blockSize = ins.readUInt32()            
            if self.tournamentSocket.bytesAvailable() < self.blockSize:
                return
            
            action = ins.readQString()
            self.process(action, ins)
            self.blockSize = 0

    def process(self, action, stream):
        logger.debug("Tournament Server: " + action)
        self.receiveJSON(action, stream)
        

    def receiveJSON(self, data_string, stream):
        '''
        A fairly pythonic way to process received strings as JSON messages.
        '''
        message = json.loads(data_string)
        cmd = "command_" + message['command']
        if hasattr(self, cmd):
            getattr(self, cmd)(message)  

    def writeToServer(self, action, *args, **kw):        
        logger.debug(("writeToServer(" + action + ", [" + ', '.join(args) + "])"))
        
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
                logger.warn("Uninterpreted Data Type: " + str(type(arg)) + " of value: " + str(arg))
                out.writeQString(str(arg))

        out.device().seek(0)
        out.writeUInt32(block.size() - 4)

        self.bytesToSend = block.size() - 4        
        self.tournamentSocket.write(block)

    def handleServerError(self, socketError):
        if socketError == QtNetwork.QAbstractSocket.RemoteHostClosedError:
            logger.info("Tournament Server down: The server is down for maintenance, please try later.")

        elif socketError == QtNetwork.QAbstractSocket.HostNotFoundError:
            logger.info("Connection to Host lost. Please check the host name and port settings.")
            
        elif socketError == QtNetwork.QAbstractSocket.ConnectionRefusedError:
            logger.info("The connection was refused by the peer.")
        else:
            logger.info("The following error occurred: %s." % self.tournamentSocket.errorString())    


    @QtCore.pyqtSlot()
    def disconnected(self):
        logger.info("Disconnected from server")


    @QtCore.pyqtSlot(QtNetwork.QAbstractSocket.SocketError)
    def errored(self, error):
        logger.error("TCP Error " + self.tournamentSocket.errorString())
