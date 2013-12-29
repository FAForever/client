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





import util
from PyQt4 import QtGui, QtCore
import time
from chat import user2name, logger
from chat.chatter import Chatter
import re          
import fa
import json

QUERY_BLINK_SPEED = 250
CHAT_TEXT_LIMIT = 350
CHAT_REMOVEBLOCK = 50

FormClass, BaseClass = util.loadUiType("chat/channel.ui")

class Channel(FormClass, BaseClass):
    '''
    This is an actual chat channel object, representing an IRC chat room and the users currently present.
    '''
    def __init__(self, lobby, name, private=False, *args, **kwargs):
        BaseClass.__init__(self, lobby, *args, **kwargs)

        self.setupUi(self)
        
        #Special HTML formatter used to layout the chat lines written by people
        self.FORMATTER_ANNOUNCEMENT        = unicode(util.readfile("chat/formatters/announcement.qthtml"))
        self.FORMATTER_MESSAGE             = unicode(util.readfile("chat/formatters/message.qthtml"))
        self.FORMATTER_MESSAGE_AVATAR      = unicode(util.readfile("chat/formatters/messageAvatar.qthtml"))
        self.FORMATTER_ACTION              = unicode(util.readfile("chat/formatters/action.qthtml"))
        self.FORMATTER_ACTION_AVATAR       = unicode(util.readfile("chat/formatters/actionAvatar.qthtml"))
        self.FORMATTER_RAW                 = unicode(util.readfile("chat/formatters/raw.qthtml"))
        self.NICKLIST_COLUMNS              = json.loads(util.readfile("chat/formatters/nicklist_columns.json"))
        self.lobby = lobby        
        self.chatters = {}
        
        self.lasttimestamp= None
        
        # Query flasher
        self.blinker = QtCore.QTimer()
        self.blinker.timeout.connect(self.blink)    
        self.blinked = False
        
        # Table width of each chatter's name cell...        
        self.maxChatterWidth = 100 # TODO: This might / should auto-adapt

        #count the number of line currently in the chat
        self.lines = 0

        # Clear window menu action
        self.lobby.client.actionClearWindow.triggered.connect(self.clearWindow)

        # Perform special setup for public channels as opposed to private ones
        self.name = name
        self.private = private
        
        self.gwChannel = False
        
        self.setup()
        
        
    def setup(self):
        if not self.private:
            # Non-query channels have a sorted nicklist
            self.nickList.sortItems(Chatter.SORT_COLUMN)
            
            #Properly and snugly snap all the columns
            self.nickList.horizontalHeader().setResizeMode(Chatter.RANK_COLUMN, QtGui.QHeaderView.Fixed)
            self.nickList.horizontalHeader().resizeSection(Chatter.RANK_COLUMN, self.NICKLIST_COLUMNS['RANK'])

            self.nickList.horizontalHeader().setResizeMode(Chatter.AVATAR_COLUMN, QtGui.QHeaderView.Fixed)
            self.nickList.horizontalHeader().resizeSection(Chatter.AVATAR_COLUMN, self.NICKLIST_COLUMNS['AVATAR'])
            
            self.nickList.horizontalHeader().setResizeMode(Chatter.STATUS_COLUMN, QtGui.QHeaderView.Fixed)
            self.nickList.horizontalHeader().resizeSection(Chatter.STATUS_COLUMN, self.NICKLIST_COLUMNS['STATUS'])
            
            self.nickList.horizontalHeader().setResizeMode(Chatter.SORT_COLUMN, QtGui.QHeaderView.Stretch)
            
            self.nickList.itemDoubleClicked.connect(self.nickDoubleClicked)
            self.nickList.itemPressed.connect(self.nickPressed)
            
            self.nickFilter.textChanged.connect(self.filterNicks)
            
            self.lobby.client.usersUpdated.connect(self.updateChatters)
        else:
            self.nickFrame.hide()
            self.announceLine.hide()

        self.chatArea.anchorClicked.connect(self.openUrl)
        self.chatEdit.returnPressed.connect(self.sendLine)
        self.chatEdit.setChatters(self.chatters)
        self.lobby.client.doneresize.connect(self.resizing)

        self.resizeTimer = QtCore.QTimer(self)
        self.resizeTimer.timeout.connect(self.canresize)
                
        
    def keyReleaseEvent(self, keyevent):
        '''
        Allow the ctrl-C event.
        '''
        if keyevent.key() == 67 :
            self.chatArea.copy()
    
    def canresize(self):
        if self.isVisible() :
            self.chatArea.setLineWrapColumnOrWidth(self.chatArea.size().width() - 20) #Hardcoded, but seems to be enough (tabstop was a bit large)
            self.resizeTimer.stop()    
        
    def resizing(self):
        self.resizeTimer.start(10)
    
   
    def showEvent(self, event):
        self.stopBlink()
        return BaseClass.showEvent(self, event)
    
    @QtCore.pyqtSlot()
    def clearWindow(self):
        if self.isVisible():
            self.chatArea.setPlainText("")
            self.lasttimestamp = 0 
        
    @QtCore.pyqtSlot()
    def filterNicks(self):
        for chatter in self.chatters.keys():
            self.chatters[chatter].setVisible(chatter.lower().find(self.nickFilter.text().lower()) >= 0)
            
    def updateUserCount(self):
        count = len(self.chatters.keys())
        self.nickFilter.setPlaceholderText(str(count) + " users... (type to search)")
            
        if self.nickFilter.text():
            self.filterNicks()
                        

    @QtCore.pyqtSlot()
    def blink(self):
        if (self.blinked):
            self.blinked = False            
            self.lobby.tabBar().setTabText(self.lobby.indexOf(self), self.name)
        else:
            self.blinked = True
            self.lobby.tabBar().setTabText(self.lobby.indexOf(self), "")
        pass

    
    @QtCore.pyqtSlot()
    def stopBlink(self):
        self.blinker.stop()
        self.lobby.tabBar().setTabText(self.lobby.indexOf(self), self.name)

        
    @QtCore.pyqtSlot()
    def startBlink(self):
        self.blinker.start(QUERY_BLINK_SPEED)
                
            
    @QtCore.pyqtSlot()    
    def pingWindow(self):
        QtGui.QApplication.alert(self.lobby.client)
            
        
        if not self.isVisible() or QtGui.QApplication.activeWindow() != self.lobby.client:
            if self.oneMinuteOrOlder():
                if self.lobby.client.soundeffects:
                    util.sound("chat/sfx/query.wav")
             
        if not self.isVisible():
            if not self.blinker.isActive() and not self == self.lobby.currentWidget():
                    self.startBlink()

        
    @QtCore.pyqtSlot(QtCore.QUrl)
    def openUrl(self, url):
        logger.debug("Clicked on URL: " + url.toString())
        if url.scheme() == "faflive":
            fa.exe.replay(url)
        elif url.scheme() == "fafgame":
            self.lobby.client.joinGameFromURL(url)
        else :
            QtGui.QDesktopServices.openUrl(url)


    @QtCore.pyqtSlot(str, str)
    def printAnnouncement(self, text, color, size, scroll_forced = True):
        '''
        Print an actual message in the chatArea of the channel
        '''                         
        # scroll if close to the last line of the log
        scroll_current = self.chatArea.verticalScrollBar().value()
        scroll_needed = scroll_forced or ((self.chatArea.verticalScrollBar().maximum() - scroll_current) < 20)

        cursor = self.chatArea.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.chatArea.setTextCursor(cursor)

        formatter = self.FORMATTER_ANNOUNCEMENT        
        line = formatter.format(size=size, color=color, text=util.irc_escape(text, self.lobby.a_style))        
        self.chatArea.insertHtml(line)
        
        if scroll_needed:
            self.chatArea.verticalScrollBar().setValue(self.chatArea.verticalScrollBar().maximum())
        else:
            self.chatArea.verticalScrollBar().setValue(scroll_current)

    def quackerize(self, text):
        line = []
        words = text.split()
        
        for word in words :
            line.append("qu"+ "a" * min(7,len(word))+ "ck")
             
        return (" ").join(line)    
 
    @QtCore.pyqtSlot(str, str)
    def printMsg(self, name, text, scroll_forced=False):
        '''
        Print an actual message in the chatArea of the channel
        '''               
        if self.lines > CHAT_TEXT_LIMIT :
            cursor = self.chatArea.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Start)
            cursor.movePosition(QtGui.QTextCursor.Down, QtGui.QTextCursor.KeepAnchor, CHAT_REMOVEBLOCK)
            cursor.removeSelectedText()
            self.lines = self.lines - CHAT_REMOVEBLOCK
        
        avatar = None
        
        if self.lobby.client.isFoe(name) :
            text = self.quackerize(text)
        
        if name.lower() in self.lobby.specialUserColors:
            color = self.lobby.specialUserColors[name.lower()]
        else:
            if name in self.chatters:
                chatter = self.chatters[name]                
                color = chatter.textColor().name()
                if chatter.avatar:
                    avatar = chatter.avatar["url"] 
                    avatarTip = chatter.avatarTip or ""
                
            else:
                color = self.lobby.client.getUserColor(name) #Fallback and ask the client. We have no Idea who this is.

        # Play a ping sound and flash the title under certain circumstances
        if self.private and name != self.lobby.client.login:
            self.pingWindow()

        if not self.private and text.find(self.lobby.client.login)!=-1:
            self.pingWindow()
            color = self.lobby.client.getColor("tous")


        # scroll if close to the last line of the log
        scroll_current = self.chatArea.verticalScrollBar().value()
        scroll_needed = scroll_forced or ((self.chatArea.verticalScrollBar().maximum() - scroll_current) < 20)

        cursor = self.chatArea.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.chatArea.setTextCursor(cursor)                
        
        if avatar :
            pix = util.respix(avatar)
            if pix:
                if not self.chatArea.document().resource(QtGui.QTextDocument.ImageResource, QtCore.QUrl(avatar)):
                    self.chatArea.document().addResource(QtGui.QTextDocument.ImageResource,  QtCore.QUrl(avatar), pix)                        
                formatter = self.FORMATTER_MESSAGE_AVATAR
                line = formatter.format(time=self.timestamp(), avatar=avatar, name=name, avatarTip=avatarTip, color=color, width=self.maxChatterWidth, text=util.irc_escape(text, self.lobby.a_style))                 
            else :
                formatter = self.FORMATTER_MESSAGE
                line = formatter.format(time=self.timestamp(), name=name, color=color, width=self.maxChatterWidth, text=util.irc_escape(text, self.lobby.a_style))        

        else :
            formatter = self.FORMATTER_MESSAGE
            line = formatter.format(time=self.timestamp(), name=name, color=color, width=self.maxChatterWidth, text=util.irc_escape(text, self.lobby.a_style))        
        
        self.chatArea.insertHtml(line)
        self.lines = self.lines + 1
        
        if scroll_needed:
            self.chatArea.verticalScrollBar().setValue(self.chatArea.verticalScrollBar().maximum())
        else:
            self.chatArea.verticalScrollBar().setValue(scroll_current)


    @QtCore.pyqtSlot(str, str)
    def printAction(self, name, text, scroll_forced=False, server_action=False):        
        '''
        Print an actual message in the chatArea of the channel
        '''
        if self.lines > CHAT_TEXT_LIMIT :
            cursor = self.chatArea.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Start)
            cursor.movePosition(QtGui.QTextCursor.Down, QtGui.QTextCursor.KeepAnchor, CHAT_REMOVEBLOCK)
            cursor.removeSelectedText()
            self.lines = self.lines - CHAT_REMOVEBLOCK        
        
        if server_action :
            color = self.lobby.client.getColor("server")
        elif name.lower() in self.lobby.specialUserColors:
            color = self.lobby.specialUserColors[name.lower()]
        else:
            color = self.lobby.client.getUserColor(name)
            
        # Play a ping sound
        if self.private and name != self.lobby.client.login:
            self.pingWindow()


        avatar = None

        if name in self.chatters:
            chatter = self.chatters[name]                
            if chatter.avatar :
                avatar = chatter.avatar["url"] 
                avatarTip = chatter.avatarTip or ""
            
        # scroll if close to the last line of the log
        scroll_current = self.chatArea.verticalScrollBar().value()
        scroll_needed = scroll_forced or ((self.chatArea.verticalScrollBar().maximum() - scroll_current) < 20)
        
        cursor = self.chatArea.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.chatArea.setTextCursor(cursor)

        if avatar :
            pix = util.respix(avatar)
            if pix:            
                if not self.chatArea.document().resource(QtGui.QTextDocument.ImageResource, QtCore.QUrl(avatar)) :
                    self.chatArea.document().addResource(QtGui.QTextDocument.ImageResource,  QtCore.QUrl(avatar), pix)
                formatter = self.FORMATTER_ACTION_AVATAR
                line = formatter.format(time=self.timestamp(), avatar=avatar, avatarTip=avatarTip, name=name, color=color, width=self.maxChatterWidth, text=util.irc_escape(text, self.lobby.a_style))
            else:            
                formatter = self.FORMATTER_ACTION
                line = formatter.format(time=self.timestamp(), name=name, color=color, width=self.maxChatterWidth, text=util.irc_escape(text, self.lobby.a_style))
        else:            
            formatter = self.FORMATTER_ACTION
            line = formatter.format(time=self.timestamp(), name=name, color=color, width=self.maxChatterWidth, text=util.irc_escape(text, self.lobby.a_style))
        
        self.chatArea.insertHtml(line)
        self.lines = self.lines + 1

        if scroll_needed:
            self.chatArea.verticalScrollBar().setValue(self.chatArea.verticalScrollBar().maximum())
        else:
            self.chatArea.verticalScrollBar().setValue(scroll_current)
        
        
    @QtCore.pyqtSlot(str, str)
    def printRaw(self, name, text, scroll_forced=False):
        '''
        Print an raw message in the chatArea of the channel
        '''
        
        if name in self.lobby.specialUserColors:
            color = self.lobby.specialUserColors[name]
        else:
            color = self.lobby.client.getUserColor(name)
            
        # Play a ping sound
        if self.private and name != self.lobby.client.login:
            self.pingWindow()
            
        # scroll if close to the last line of the log
        scroll_current = self.chatArea.verticalScrollBar().value()
        scroll_needed = scroll_forced or ((self.chatArea.verticalScrollBar().maximum() - scroll_current) < 20)
        
        cursor = self.chatArea.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.chatArea.setTextCursor(cursor)
                            
        formatter = self.FORMATTER_RAW
        line = formatter.format(time=self.timestamp(), name=name, color=color, width=self.maxChatterWidth, text=text)
        self.chatArea.insertHtml(line)
        
        if scroll_needed:
            self.chatArea.verticalScrollBar().setValue(self.chatArea.verticalScrollBar().maximum())
        else:
            self.chatArea.verticalScrollBar().setValue(scroll_current)
                
        
    def timestamp(self):
        '''returns a fresh timestamp string once every minute, and an empty string otherwise'''
        timestamp = time.strftime("%H:%M")
        if self.lasttimestamp != timestamp:
            self.lasttimestamp = timestamp
            return timestamp
        else:
            return ""

    def oneMinuteOrOlder(self):
        timestamp = time.strftime("%H:%M")
        return self.lasttimestamp != timestamp
        
    
    @QtCore.pyqtSlot(QtGui.QTableWidgetItem)
    def nickDoubleClicked(self, item):
        chatter = self.nickList.item(item.row(), Chatter.SORT_COLUMN) #Look up the associated chatter object          
        chatter.doubleClicked(item)
        pass


    @QtCore.pyqtSlot(QtGui.QTableWidgetItem)
    def nickPressed(self, item):
        if QtGui.QApplication.mouseButtons() == QtCore.Qt.RightButton:            
            #Look up the associated chatter object
            chatter = self.nickList.item(item.row(), Chatter.SORT_COLUMN)           
            chatter.pressed(item)


    @QtCore.pyqtSlot(list)    
    def updateChatters(self, chatters):
        ''' 
        Updates the status, icon and color of an IRC user depending on its known state in the FAF client
        Takes a list of users.
        '''
        for name in chatters:            
            if name in self.chatters: 
                self.chatters[name].update() #only update chatters that are in this channel
        
        self.updateUserCount()
        
    def elevateChatter(self, name, modes):
        add = re.compile(".*\+([a-z]+)")
        remove = re.compile(".*\-([a-z]+)")
        if name in self.chatters:
            addmatch = re.search(add, modes)
            if addmatch:
                modes = addmatch.group(1)
                mode = ""
                if "v" in modes:
                    mode = "+"
                if "o" in modes:
                    mode = "@"
                if "q" in modes:
                    mode = "~"                    
                if mode in self.lobby.OPERATOR_COLORS:
                    self.chatters[name].elevation = mode
                    self.chatters[name].update()
            removematch = re.search(remove, modes)
            if removematch:
                modes = removematch.group(1)
                mode = ""
                if "o" in modes and self.chatters[name].elevation == "@":
                    self.chatters[name].elevation = None
                    self.chatters[name].update()
                if "q" in modes and self.chatters[name].elevation == "~":
                    self.chatters[name].elevation = None
                    self.chatters[name].update()
                if "v" in modes and self.chatters[name].elevation == "+":
                    self.chatters[name].elevation = None
                    self.chatters[name].update()
        
    def addChatter(self, user, join = False):
        '''
        Adds an user to this chat channel, and assigns an appropriate icon depending on friendship and FAF player status
        '''          
        name = user2name(user)

        if name not in self.chatters:
            item = Chatter(self.nickList, user, self.lobby, None)                        
            self.chatters[name] = item        
            
        self.chatters[name].update()

        self.updateUserCount()
        
        if join and self.lobby.client.joinsparts:
            self.printAction(name, "joined the channel.", server_action=True)
    
    
    def removeChatter(self, name, action = None):
        if name in self.chatters:
            self.nickList.removeRow(self.chatters[name].row())        
            del self.chatters[name]

            if action and (self.lobby.client.joinsparts or self.private):
                self.printAction(name, action, server_action=True)
                self.stopBlink()


        self.updateUserCount()


    def setAnnounceText(self,text):
        self.announceLine.clear()
        self.announceLine.setText("<style>a{color:cornflowerblue}</style><b><font color=white>" + util.irc_escape(text) + "</font></b>")

    
    @QtCore.pyqtSlot()
    def sendLine(self, target=None):
        self.stopBlink()
        
        if not target:
            target = self.name #pubmsg in channel
                        
        line = self.chatEdit.text()
        #Split into lines if newlines are present
        fragments = line.split("\n")
        for text in fragments:            
            # Compound wacky Whitespace
            text = re.sub('\s', ' ', text)
            text = text.strip()
            
            # Reject empty messages
            if not text: 
                continue
                
            # System commands        
            if text[0] == "/":
                if text.startswith(("/topic ")):
                    self.lobby.setTopic(self.name,text[7:])
                elif text.startswith(("/me ")):
                    if self.lobby.sendAction(target, text[4:]):
                        self.printAction(self.lobby.client.login, text[4:], True)
                    else:
                        self.printAction("IRC", "action not supported", True)
                elif text.startswith(("/seen ")):
                    if self.lobby.sendMsg("nickserv", "info %s" % (text[6:])):
                        self.printAction("IRC", "info requested on %s" % (text[6:]), True)
                    else:
                        self.printAction("IRC", "not connected", True)
            else:
                if self.lobby.sendMsg(target, text):
                    self.printMsg(self.lobby.client.login, text, True)
                    if target.lower() == "#uef" or target.lower() == "#aeon" or target.lower() == "#cybran" or target.lower() == "#seraphim" :
                        if self.gwChannel == True:
                            # we need to send to the "normal" chat too
                            if target in self.lobby.client.chat.channels:
                                self.lobby.client.chat.channels[target].printMsg(self.lobby.client.login, text, True)
                        else:
                            # we need to send to the GW chat too
                            self.lobby.client.GalacticWar.channel.printMsg(self.lobby.client.login, text, True)
        
        self.chatEdit.clear()
        
        
        
