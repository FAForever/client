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





from PyQt4 import QtGui, QtCore
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest

from chat.irclib import SimpleIRCClient
import util
import fa

import sys
from chat import logger, user2name
from chat.channel import Channel

IRC_PORT = 8167
IRC_SERVER = "direct.faforever.com"
POLLING_INTERVAL = 300   # milliseconds between irc polls

                
FormClass, BaseClass = util.loadUiType("chat/chat.ui")
                
class ChatWidget(FormClass, BaseClass, SimpleIRCClient):
    '''
    This is the chat lobby module for the FAF client. 
    It manages a list of channels and dispatches IRC events (lobby inherits from irclib's client class
    '''
    def __init__(self, client, *args, **kwargs):
        logger.debug("Lobby instantiating.")
        BaseClass.__init__(self, *args, **kwargs)
        SimpleIRCClient.__init__(self)

        self.setupUi(self)
        
        
        # CAVEAT: These will fail if loaded before theming is loaded
        import json
        self.OPERATOR_COLORS = json.loads(util.readfile("chat/formatters/operator_colors.json"))
        
        self.client = client
        self.channels = {}
        
        #avatar downloader
        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.finishDownloadAvatar)
                    
        #nickserv stuff
        self.identified = False
        
        #IRC parameters
        self.ircServer = IRC_SERVER
        self.ircPort = IRC_PORT
        self.crucialChannels = ["#aeolus"]
        self.optionalChannels = []

        #We can't send command until the welcom message is received
        self.welcomed = False

        # Load colors and styles from theme
        self.specialUserColors = json.loads(util.readfile("chat/formatters/special_colors.json"))
        self.a_style = util.readfile("chat/formatters/a_style.qss") 
        
        #load UI perform some tweaks
        self.tabBar().setTabButton(0, 1, None)
        
        #add self to client's window
        self.client.chatTab.layout().addWidget(self)        
        self.tabCloseRequested.connect(self.closeChannel)

        #add signal handler for game exit
        self.client.gameExit.connect(self.processGameExit)
        self.replayInfo = fa.exe.instance.info
        

        #Hook with client's connection and autojoin mechanisms
        self.client.connected.connect(self.connect)
        self.client.publicBroadcast.connect(self.announce)
        self.client.autoJoin.connect(self.autoJoin)
    
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.poll)

   
    @QtCore.pyqtSlot()
    def poll(self):
        self.timer.stop()
        self.once()
        self.timer.start(POLLING_INTERVAL)
    
    
    def disconnect(self):
        self.irc_disconnect()
        self.timer.stop()


    @QtCore.pyqtSlot()
    def connect(self):
        #Do the actual connecting, join all important channels
        try:
            self.irc_connect(self.ircServer, self.ircPort, self.client.login, ssl=True)
           
            self.timer.start();
            
        except:
            logger.debug("Unable to connect to IRC server.")
            self.serverLogArea.appendPlainText("Unable to connect to the chat server, but you should still be able to host and join games.")
            logger.error("IRC Exception", exc_info=sys.exc_info())

    
    def finishDownloadAvatar(self, reply):
        ''' this take care of updating the avatars of players once they are downloaded '''
        img = QtGui.QImage()
        img.loadFromData(reply.readAll())
        pix = util.respix(reply.url().toString())
        if pix :
            pix = QtGui.QIcon(QtGui.QPixmap(img))
        else :
            util.addrespix(reply.url().toString(), QtGui.QPixmap(img))
            
        for player in util.curDownloadAvatar(reply.url().toString()) :
            for channel in self.channels :
                if player in self.channels[channel].chatters :
                    self.channels[channel].chatters[player].avatarItem.setIcon(QtGui.QIcon(util.respix(reply.url().toString())))
                    self.channels[channel].chatters[player].avatarItem.setToolTip(self.channels[channel].chatters[player].avatarTip)
            
            if self.client.GalacticWar.channel != None :
                if player in self.client.GalacticWar.channel.chatters :
                    self.client.GalacticWar.channel.chatters[player].avatarItem.setIcon(QtGui.QIcon(util.respix(reply.url().toString())))
                    self.client.GalacticWar.channel.chatters[player].avatarItem.setToolTip(self.client.GalacticWar.channel.chatters[player].avatarTip)
            
                   
    def closeChannel(self, index):
        '''
        Closes a channel tab.
        '''
        channel = self.widget(index)
        for name in self.channels:
                if self.channels[name] is channel:
                    if not self.channels[name].private and self.connection.is_connected():     # Channels must be parted (if still connected)
                        self.connection.part([name], "tab closed")   
                    else:
                        # Queries and disconnected channel windows can just be closed
                        self.removeTab(index)
                        del self.channels[name]
                    
                    break

    @QtCore.pyqtSlot(str)
    def announce(self, broadcast):
        ''' 
        Notifies all crucial channels about the status of the client.
        '''        
        logger.debug("BROADCAST:" + broadcast)
        for channel in self.crucialChannels:
            self.sendMsg(channel, broadcast)



    def sendMsg(self, target, text):
        if self.connection.is_connected():
            self.connection.privmsg(target, text)
            return True
        else:
            logger.error("IRC connection lost.")
            for channel in self.crucialChannels:
                if channel in self.channels:                
                    self.channels[channel].printAction("IRC", "was disconnected.")
            return False            

        

    def sendAction(self, target, text):
        if self.connection.is_connected():
            self.connection.action(target, text)
            return True            
        else:
            logger.error("IRC connection lost.")
            for channel in self.crucialChannels:
                if channel in self.channels:               
                    self.channels[channel].printAction("IRC", "was disconnected.")            
            return False            



    def openQuery(self, name, activate=False):
        # In developer mode, allow player to talk to self to test chat functions
        if (name == self.client.login) and not util.developer():
            return False
        
        #not allowing foes to talk to us.
        if (self.client.isFoe(name)) :
            return False
        
        if name not in self.channels:
            self.channels[name] = Channel(self, name, True)
            self.addTab(self.channels[name], user2name(name))
        
        if activate:
            self.setCurrentWidget(self.channels[name])
            
        self.channels[name].resizing()
        return True
        
        
        
    @QtCore.pyqtSlot(list)
    def autoJoin(self, channels):
            for channel in channels:
                if (self.connection.is_connected()) and self.welcomed:
                    #directly join
                    self.connection.join(channel)
                else:
                    #Note down channels for later.
                    self.optionalChannels.append(channel)

    def processGameExit(self):
        self.autopostjoin = util.settings.value("chat/autopostjoin")
        logger.info("autopostjoin: " + str(self.autopostjoin))
        if (str(self.autopostjoin) == "true"):
            self.replayInfo = fa.exe.instance.info
            if self.replayInfo:
                if 'num_players' in self.replayInfo:
                    self.nrofplayers = int(self.replayInfo['num_players'])
                    logger.info("nr of players: " + str(self.nrofplayers))
                    if (self.nrofplayers > 1):
                        postGameChannel = "#game-" + str(self.replayInfo['uid'])
                        if (self.connection.is_connected()):
                            logger.info("Joining post-game channel.")
                            self.connection.join(postGameChannel)
        
        
        
#SimpleIRCClient Class Dispatcher Attributes follow here.
    def on_welcome(self, c, e):
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))
        self.welcomed = True
        
        
    def nickservIdentify(self):
        if self.identified == False :
            self.serverLogArea.appendPlainText("[Identify as : %s]" % (self.client.login))
            self.connection.privmsg('NickServ', 'identify %s %s' % (self.client.login, util.md5text(self.client.password)))
    
    def on_authentified(self):
        if self.connection.get_nickname() != self.client.login :
            self.serverLogArea.appendPlainText("[Retrieving our nickname : %s]" % (self.client.login))
            self.connection.privmsg('nickserv', 'recover %s %s' % (self.client.login, util.md5text(self.client.password)))
        #Perform any pending autojoins (client may have emitted autoJoin signals before we talked to the IRC server)
        self.autoJoin(self.optionalChannels)
        self.autoJoin(self.crucialChannels)
    
    def nickservRegister(self):
        self.connection.privmsg('NickServ', 'register %s %s' % (util.md5text(self.client.password), self.client.email))
        
        
    def on_version(self, c, e):
        self.connection.privmsg(e.source(), "Forged Alliance Forever " + self.client.VERSION)
      
      
    def on_motd(self, c, e):   
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))
        self.nickservIdentify()
   
    def on_endofmotd(self, c, e):   
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))
   
        
    def on_namreply(self, c, e):        
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))
        channel = e.arguments()[1]
        listing = e.arguments()[2].split()

        for user in listing:
            self.channels[channel].addChatter(user)
            
        
            if self.client.GalacticWar.channel and channel == self.client.GalacticWar.channel.name :
                self.client.GalacticWar.channel.addChatter(user)
                
            QtGui.QApplication.processEvents()      #Added by thygrrr to improve application responsiveness on large IRC packets
        
        logger.debug("Added " + str(len(listing)) + " Chatters")

               
                    
    def on_whoisuser(self, c, e):
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))
        
        
    def on_join(self, c, e):
        channel = e.target()
        
        # If we're joining, we need to open the channel for us first.
        if channel not in self.channels:
            self.channels[channel] = Channel(self, channel)
            if (channel.lower() in self.crucialChannels):
                self.insertTab(1, self.channels[channel], channel)    #CAVEAT: This is assumes a server tab exists.                
                self.client.localBroadcast.connect(self.channels[channel].printRaw)
                self.channels[channel].printAnnouncement("Welcome to Forged Alliance Forever !", "red", "+3") 
                self.channels[channel].printAnnouncement("The documentation is the wiki. Check the Links menu !", "red", "+1") 
                self.channels[channel].printAnnouncement("", "black", "+1") 
                self.channels[channel].printAnnouncement("", "black", "+1")
                
            else:
                if channel.lower() == "#uef" or channel.lower() == "#aeon" or channel.lower() == "#cybran" or channel.lower() == "#seraphim" :
                    self.client.GalacticWar.createChannel(self, channel)
                    self.client.GalacticWar.network_Chat.layout().addWidget(self.client.GalacticWar.channel) 
                    self.client.GalacticWar.channel.addChatter(user2name(e.source()), True)
                    self.client.GalacticWar.channel.resizing()

                self.addTab(self.channels[channel], channel)
            
            
            if channel.lower() in self.crucialChannels: #Make the crucial channels not closeable, and make the last one the active one
                self.setCurrentWidget(self.channels[channel])
                self.tabBar().setTabButton(self.currentIndex(), QtGui.QTabBar.RightSide, None)

        self.channels[channel].addChatter(user2name(e.source()), True)
        self.channels[channel].resizing()
        
    
  
    
    def on_part(self, c, e):
        channel = e.target()
        name = user2name(e.source())
        if name == self.client.login:   #We left ourselves.
            self.removeTab(self.indexOf(self.channels[channel]))
            del self.channels[channel]
        else:                           #Someone else left
            self.channels[channel].removeChatter(name, "left.")
                
                
    def on_quit(self, c, e):
        name = user2name(e.source())
        for channel in self.channels:
            if (not self.channels[channel].private) or (self.channels[channel].name == user2name(name)):
                self.channels[channel].removeChatter(name, "quit.")
        
        
    def on_nick(self, c, e):
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))
    
    
    def on_umode(self, c, e):        
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))


    def on_notice(self, c, e):
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))


    def on_currenttopic(self, c, e):
        channel = e.arguments()[0]
        if channel in self.channels:
            self.channels[channel].printMsg(channel, "\n".join(e.arguments()[1:]))        


    def on_topicinfo(self, c, e):
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))
                 
                    
    def on_list(self, c, e):
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))


    def on_bannedfromchan(self, c, e):
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))


    def on_pubmsg(self, c, e):        
        target = e.target()
        
        if target in self.channels:
            self.channels[target].printMsg(user2name(e.source()), "\n".join(e.arguments()))
        if self.client.GalacticWar.channel and target == self.client.GalacticWar.channel.name :
            self.client.GalacticWar.channel.printMsg(user2name(e.source()), "\n".join(e.arguments()))
                        
    def on_privnotice(self, c, e):                            
        source = user2name(e.source())
        notice = e.arguments()[0]
        prefix = notice.split(" ")[0]
        target = prefix.strip("[]")
        
        if source and source.lower() == 'nickserv':
            
            if e.arguments()[0].find("registered under your account") >= 0:
                if self.identified == False :
                    self.identified = True
                    self.on_authentified()
                
            elif e.arguments()[0].find("isn't registered") >= 0:
                
                self.nickservRegister()
        
            elif e.arguments()[0].find("Password accepted") :
                if self.identified == False :
                    self.identified = True
                    self.on_authentified()
                        
            elif e.arguments()[0].find("RELEASE") >= 0:
                self.connection.privmsg('nickserv', 'release %s %s' % (self.client.login, util.md5text(self.client.password)))

            elif e.arguments()[0].find("hold on") >= 0:
                self.connection.nick(self.client.login)

        message = "\n".join(e.arguments()).lstrip(prefix)
        if target in self.channels:
            self.channels[target].printMsg(source, message)     
              
                                                            
    def on_privmsg(self, c, e):
        name = user2name(e.source())
        
        if self.client.isFoe(name) :
            return
        # Create a Query if it's not open yet, and post to it if it exists.
        if self.openQuery(name):
            self.channels[name].printMsg(name, "\n".join(e.arguments()))
        
        
    def on_action(self, c, e):
        name = user2name(e.source())
        target = e.target()

        if self.client.isFoe(name) :
            return
        
        # Create a Query if it's not an action intended for a channel
        if target not in self.channels:
            self.openQuery(name)
            self.channels[name].printAction(name, "\n".join(e.arguments()))
        else:
            self.channels[target].printAction(name, "\n".join(e.arguments()))
        
    def on_default(self, c, e):                     
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))
        if "Nickname is already in use." in "\n".join(e.arguments()) :
            self.connection.nick(self.client.login + "_")

