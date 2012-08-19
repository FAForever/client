import util
from PyQt4 import QtGui, QtCore
import time
from chat import user2name, logger
from chat.chatter import Chatter
import re          
import fa
import json

QUERY_BLINK_SPEED = 250
CHAT_TEXT_LIMIT = 400
       
FormClass, BaseClass = util.loadUiType("chat/channel.ui")

class Channel(FormClass, BaseClass):
    '''
    This is an actual chat channel object, representing an IRC chat room and the users currently present.
    '''
    def __init__(self, lobby, name, private=False, *args, **kwargs):
        FormClass.__init__(self, lobby, *args, **kwargs)
        BaseClass.__init__(self, lobby, *args, **kwargs)

        self.setupUi(self)
        
        #Special HTML formatter used to layout the chat lines written by people
        self.FORMATTER_ANNOUNCEMENT = unicode(util.readfile("chat/formatters/announcement.qthtml"))
        self.FORMATTER_MESSAGE      = unicode(util.readfile("chat/formatters/message.qthtml"))
        self.FORMATTER_ACTION       = unicode(util.readfile("chat/formatters/action.qthtml"))
        self.FORMATTER_RAW          = unicode(util.readfile("chat/formatters/raw.qthtml"))
        self.NICKLIST_COLUMNS       = json.loads(util.readfile("chat/formatters/nicklist_columns.json"))
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

        # Perform special setup for public channels as opposed to private ones
        self.name = name
        self.private = private
        if not private:
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

        self.chatArea.anchorClicked.connect(self.openUrl)
        self.chatEdit.returnPressed.connect(self.sendLine)
        self.chatEdit.setChatters(self.chatters)
        self.lobby.client.doneresize.connect(self.resizing)

        
    def keyReleaseEvent(self, keyevent):
        '''
        Allow the ctrl-C event.
        '''
        if keyevent.key() == 67 :
            self.chatArea.copy()
            
    def resizing(self):
        self.chatArea.setLineWrapColumnOrWidth(self.chatArea.size().width()-self.chatArea.tabStopWidth())
   
    def showEvent(self, event):
        self.stopBlink()
        return BaseClass.showEvent(self, event)
    

    @QtCore.pyqtSlot()
    def filterNicks(self):
        for chatter in self.chatters.keys():
            self.chatters[chatter].setVisible(chatter.lower().find(self.nickFilter.text().lower()) >= 0)
            
    def updateUserCount(self):
        count = len(self.chatters.keys())
        if count < 300:
            self.nickFilter.setPlaceholderText(str(count) + " users...")
        else:
            self.nickFilter.setPlaceholderText(str(count) + " users... (beat this, Halcyon!)")
            
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
        line = formatter.format(time=self.timestamp(), size=size, color=color, text=util.irc_escape(text, self.lobby.a_style))        
        self.chatArea.insertHtml(line)
        
        if scroll_needed:
            self.chatArea.verticalScrollBar().setValue(self.chatArea.verticalScrollBar().maximum())
        else:
            self.chatArea.verticalScrollBar().setValue(scroll_current)
    
 
    @QtCore.pyqtSlot(str, str)
    def printMsg(self, name, text, scroll_forced=False):
        '''
        Print an actual message in the chatArea of the channel
        '''               
        if self.lines > CHAT_TEXT_LIMIT :
            
            cursor = self.chatArea.textCursor()

            cursor.movePosition(QtGui.QTextCursor.Start)
            cursor.movePosition(QtGui.QTextCursor.Down)
            cursor.select(QtGui.QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            self.lines = self.lines - 1
            
        if name.lower() in self.lobby.specialUserColors:
            color = self.lobby.specialUserColors[name.lower()]
        else:
            if name in self.chatters:
                chatter = self.chatters[name]                
                color = chatter.textColor().name()
            else:
                color = self.lobby.client.getUserColor(name) #Fallback and ask the client. We have no Idea who this is.

        # Play a ping sound and flash the title under certain circumstances
        if self.private and name != self.lobby.client.login:
            self.pingWindow()


        # scroll if close to the last line of the log
        scroll_current = self.chatArea.verticalScrollBar().value()
        scroll_needed = scroll_forced or ((self.chatArea.verticalScrollBar().maximum() - scroll_current) < 20)

        cursor = self.chatArea.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.chatArea.setTextCursor(cursor)

        formatter = self.FORMATTER_MESSAGE
        line = formatter.format(time=self.timestamp(), name=name, color=color, width=self.maxChatterWidth, text=util.irc_escape(text, self.lobby.a_style))        
        self.chatArea.insertHtml(line)
        self.lines = self.lines + 1
        
        if scroll_needed:
            self.chatArea.verticalScrollBar().setValue(self.chatArea.verticalScrollBar().maximum())
        else:
            self.chatArea.verticalScrollBar().setValue(scroll_current)


    @QtCore.pyqtSlot(str, str)
    def printAction(self, name, text, scroll_forced=False):        
        '''
        Print an actual message in the chatArea of the channel
        '''            
        if name.lower() in self.lobby.specialUserColors:
            color = self.lobby.specialUserColors[name.lower()]
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
            
        formatter = self.FORMATTER_ACTION
        line = formatter.format(time=self.timestamp(), name=name, color=color, width=self.maxChatterWidth, text=util.irc_escape(text, self.lobby.a_style))
        self.chatArea.insertHtml(line)

        if scroll_needed:
            self.chatArea.verticalScrollBar().setValue(self.chatArea.verticalScrollBar().maximum())
        else:
            self.chatArea.verticalScrollBar().setValue(scroll_current)
        
        
    @QtCore.pyqtSlot(str, str)
    def printRaw(self, name, text, scroll_forced=False):
        '''
        Print an raw message in the chatArea of the channel
        '''
        
        if self.lines > CHAT_TEXT_LIMIT :
            
            cursor = self.chatArea.textCursor()

            cursor.movePosition(QtGui.QTextCursor.Start)
            cursor.movePosition(QtGui.QTextCursor.Down)
            cursor.select(QtGui.QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            self.lines = self.lines - 1
                    
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
        
        self.lines = self.lines + 1

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
            self.printAction(name, "joined the channel.")
    
    
    def removeChatter(self, name, action = None):
        if action and (self.lobby.client.joinsparts or self.private):
            self.printAction(name, action)

        if name in self.chatters:
            self.nickList.removeRow(self.chatters[name].row())        
            del self.chatters[name]

        self.updateUserCount()


    
    
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
                if text.startswith(("/me ")):            
                    if self.lobby.sendAction(target, text[4:]):
                        self.printAction(self.lobby.client.login, text[4:], True)
                    else:
                        self.printAction("IRC", "action not supported", True)
            else:
                if self.lobby.sendMsg(target, text):
                    self.printMsg(self.lobby.client.login, text, True)
        
        self.chatEdit.clear()
        
        
        