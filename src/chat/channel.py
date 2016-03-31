
from fa.replay import replay


import util
from PyQt4 import QtGui, QtCore
import time
import chat
from chat import user2name, parse_irc_source, logger
from chat.chatter import Chatter
import re          
import fa
import json
import unicodedata

from client import Player

QUERY_BLINK_SPEED = 250
CHAT_TEXT_LIMIT = 350
CHAT_REMOVEBLOCK = 50

FormClass, BaseClass = util.loadUiType("chat/channel.ui")


class IRCPlayer(Player):
    def __init__(self, name):
        Player.__init__(self, **{
            "id": -1,
            "login": name,
            "global_rating": (1500, 500),
            "ladder_rating": (1500, 500),
            "number_of_games": 0
        })


class Formatters(object):
    FORMATTER_ANNOUNCEMENT        = unicode(util.readfile("chat/formatters/announcement.qthtml"))
    FORMATTER_MESSAGE             = unicode(util.readfile("chat/formatters/message.qthtml"))
    FORMATTER_MESSAGE_AVATAR      = unicode(util.readfile("chat/formatters/messageAvatar.qthtml"))
    FORMATTER_ACTION              = unicode(util.readfile("chat/formatters/action.qthtml"))
    FORMATTER_ACTION_AVATAR       = unicode(util.readfile("chat/formatters/actionAvatar.qthtml"))
    FORMATTER_RAW                 = unicode(util.readfile("chat/formatters/raw.qthtml"))
    NICKLIST_COLUMNS              = json.loads(util.readfile("chat/formatters/nicklist_columns.json"))


class Channel(FormClass, BaseClass):
    '''
    This is an actual chat channel object, representing an IRC chat room and the users currently present.
    '''
    def __init__(self, lobby, name, private=False, *args, **kwargs):
        BaseClass.__init__(self, lobby, *args, **kwargs)

        self.setupUi(self)
        
        #Special HTML formatter used to layout the chat lines written by people
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
        
        if not self.private:
            # Non-query channels have a sorted nicklist
            self.nickList.sortItems(Chatter.SORT_COLUMN)
            
            #Properly and snugly snap all the columns
            self.nickList.horizontalHeader().setResizeMode(Chatter.RANK_COLUMN, QtGui.QHeaderView.Fixed)
            self.nickList.horizontalHeader().resizeSection(Chatter.RANK_COLUMN, Formatters.NICKLIST_COLUMNS['RANK'])

            self.nickList.horizontalHeader().setResizeMode(Chatter.AVATAR_COLUMN, QtGui.QHeaderView.Fixed)
            self.nickList.horizontalHeader().resizeSection(Chatter.AVATAR_COLUMN, Formatters.NICKLIST_COLUMNS['AVATAR'])
            
            self.nickList.horizontalHeader().setResizeMode(Chatter.STATUS_COLUMN, QtGui.QHeaderView.Fixed)
            self.nickList.horizontalHeader().resizeSection(Chatter.STATUS_COLUMN, Formatters.NICKLIST_COLUMNS['STATUS'])
            
            self.nickList.horizontalHeader().setResizeMode(Chatter.SORT_COLUMN, QtGui.QHeaderView.Stretch)
            
            self.nickList.itemDoubleClicked.connect(self.nickDoubleClicked)
            self.nickList.itemPressed.connect(self.nickPressed)
            
            self.nickFilter.textChanged.connect(self.filterNicks)
            
            self.lobby.client.usersUpdated.connect(self.update_users)
        else:
            self.nickFrame.hide()
            self.announceLine.hide()

        self.chatArea.anchorClicked.connect(self.openUrl)
        self.chatEdit.returnPressed.connect(self.sendLine)
        self.chatEdit.setChatters(self.chatters)

        self.lobby.client.doneresize.connect(self.resizing)

        self.resizeTimer = QtCore.QTimer(self)
        self.resizeTimer.timeout.connect(self.canresize)
                
    def joinChannel(self, index):
        ''' join another channel'''
        channel = self.channelsComboBox.itemText(index)
        if channel.startswith('#'):
            self.lobby.autoJoin([channel])

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
            self.chatters[chatter].setVisible(self.chatters[chatter].isFiltered(self.nickFilter.text().lower()))
            
    def updateUserCount(self):
        count = len(self.chatters.keys())
        self.nickFilter.setPlaceholderText(str(count) + " users... (type to filter)")
            
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
            replay(url)
        elif url.scheme() == "fafgame":
            self.lobby.client.joinGameFromURL(url)
        else :
            QtGui.QDesktopServices.openUrl(url)


    @QtCore.pyqtSlot(str, str)
    def printAnnouncement(self, text, color, size, scroll_forced = True):
        # scroll if close to the last line of the log
        scroll_current = self.chatArea.verticalScrollBar().value()
        scroll_needed = scroll_forced or ((self.chatArea.verticalScrollBar().maximum() - scroll_current) < 20)

        cursor = self.chatArea.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.chatArea.setTextCursor(cursor)

        formatter = Formatters.FORMATTER_ANNOUNCEMENT
        line = formatter.format(size=size, color=color, text=util.irc_escape(text, self.lobby.a_style))        
        self.chatArea.insertHtml(line)
        
        if scroll_needed:
            self.chatArea.verticalScrollBar().setValue(self.chatArea.verticalScrollBar().maximum())
        else:
            self.chatArea.verticalScrollBar().setValue(scroll_current)

    def printLine(self, name, text, scroll_forced=False, formatter=Formatters.FORMATTER_MESSAGE):
        if self.lines > CHAT_TEXT_LIMIT:
            cursor = self.chatArea.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Start)
            cursor.movePosition(QtGui.QTextCursor.Down, QtGui.QTextCursor.KeepAnchor, CHAT_REMOVEBLOCK)
            cursor.removeSelectedText()
            self.lines = self.lines - CHAT_REMOVEBLOCK

        player = self.lobby.client.players.get(name, IRCPlayer(name))

        displayName = name
        if player.clan is not None:
            displayName = "<b>[%s]</b>%s" % (player.clan, name)

        # Play a ping sound and flash the title under certain circumstances
        mentioned = text.find(self.lobby.client.login) != -1
        if mentioned or (self.private and not (formatter is Formatters.FORMATTER_RAW and  text=="quit.")):
            self.pingWindow()

        avatar = None
        if name in self.chatters:
            chatter = self.chatters[name]
            color = chatter.textColor().name()
            if chatter.avatar:
                avatar = chatter.avatar["url"]
                avatarTip = chatter.avatarTip or ""

        else:
            # Fallback and ask the client. We have no Idea who this is.
            color = self.lobby.client.players.getUserColor(name)

        if mentioned:
            color = self.lobby.client.getColor("you")

        # scroll if close to the last line of the log
        scroll_current = self.chatArea.verticalScrollBar().value()
        scroll_needed = scroll_forced or ((self.chatArea.verticalScrollBar().maximum() - scroll_current) < 20)

        cursor = self.chatArea.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.chatArea.setTextCursor(cursor)

        # This whole block seems to be duplicated further up.
        # For fucks sake.
        if avatar:
            pix = util.respix(avatar)
            if pix:
                if not self.chatArea.document().resource(QtGui.QTextDocument.ImageResource, QtCore.QUrl(avatar)) :
                    self.chatArea.document().addResource(QtGui.QTextDocument.ImageResource,  QtCore.QUrl(avatar), pix)
                line = formatter.format(time=self.timestamp(), avatar=avatar, avatarTip=avatarTip, name=displayName, color=color, width=self.maxChatterWidth, text=util.irc_escape(text, self.lobby.a_style))
            else:
                formatter = Formatters.FORMATTER_MESSAGE
                line = formatter.format(time=self.timestamp(), name=displayName, color=color, width=self.maxChatterWidth, text=util.irc_escape(text, self.lobby.a_style))
        else:
            line = formatter.format(time=self.timestamp(), name=displayName, color=color, width=self.maxChatterWidth, text=util.irc_escape(text, self.lobby.a_style))

        self.chatArea.insertHtml(line)
        self.lines = self.lines + 1

        if scroll_needed:
            self.chatArea.verticalScrollBar().setValue(self.chatArea.verticalScrollBar().maximum())
        else:
            self.chatArea.verticalScrollBar().setValue(scroll_current)

    @QtCore.pyqtSlot(str, str)
    def printMsg(self, name, text, scroll_forced=False):
        if name in self.chatters and self.chatters[name].avatar:
            fmt = Formatters.FORMATTER_MESSAGE_AVATAR
        else:
            fmt = Formatters.FORMATTER_MESSAGE
        self.printLine(name, text, scroll_forced, fmt)

    @QtCore.pyqtSlot(str, str)
    def printAction(self, name, text, scroll_forced=False, server_action=False):
        if server_action:
            fmt = Formatters.FORMATTER_RAW
        elif name in self.chatters and self.chatters[name].avatar:
            fmt = Formatters.FORMATTER_ACTION_AVATAR
        else:
            fmt = Formatters.FORMATTER_ACTION
        self.printLine(name, text, scroll_forced, fmt)

    @QtCore.pyqtSlot(str, str)
    def printRaw(self, name, text, scroll_forced=False):
        '''
        Print an raw message in the chatArea of the channel
        '''
        try:
            color = self.lobby.client.players.getUserColor(name)
                
            # Play a ping sound
            if self.private and name != self.lobby.client.login:
                self.pingWindow()
                
            # scroll if close to the last line of the log
            scroll_current = self.chatArea.verticalScrollBar().value()
            scroll_needed = scroll_forced or ((self.chatArea.verticalScrollBar().maximum() - scroll_current) < 20)
            
            cursor = self.chatArea.textCursor()
            cursor.movePosition(QtGui.QTextCursor.End)
            self.chatArea.setTextCursor(cursor)
                                
            formatter = Formatters.FORMATTER_RAW
            line = formatter.format(time=self.timestamp(), name=name, color=color, width=self.maxChatterWidth, text=text)
            self.chatArea.insertHtml(line)
            
            if scroll_needed:
                self.chatArea.verticalScrollBar().setValue(self.chatArea.verticalScrollBar().maximum())
            else:
                self.chatArea.verticalScrollBar().setValue(scroll_current)
        except:
            pass

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

    @QtCore.pyqtSlot(QtGui.QTableWidgetItem)
    def nickPressed(self, item):
        if QtGui.QApplication.mouseButtons() == QtCore.Qt.RightButton:            
            #Look up the associated chatter object
            chatter = self.nickList.item(item.row(), Chatter.SORT_COLUMN)           
            chatter.pressed(item)


    @QtCore.pyqtSlot(list)
    def update_users(self, updated_users):
        for id in updated_users:
            if id in self.lobby.client.players:
                name = self.lobby.client.players[id].login
            else:
                name = id
            if name in self.chatters:
                self.chatters[name].update()
        
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
                if mode in chat.colors.OPERATOR_COLORS:
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
        
    def addChatter(self, name, id=-1, elevation='', hostname='', join=False):
        '''
        Adds an user to this chat channel, and assigns an appropriate icon depending on friendship and FAF player status
        '''
        if name not in self.chatters:
            item = Chatter(self.nickList, (name, id, elevation, hostname), self.lobby, None)
            self.chatters[name] = item
            
        self.chatters[name].update()

        self.updateUserCount()
        
        if join and self.lobby.client.joinsparts:
            self.printAction(name, "joined the channel.", server_action=True)
    
    def removeChatter(self, name, server_action=None):
        if name in self.chatters:
            self.nickList.removeRow(self.chatters[name].row())        
            del self.chatters[name]

            if server_action and (self.lobby.client.joinsparts or self.private):
                self.printAction(name, server_action, server_action=True)
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
            if text.startswith("/"):
                if text.startswith(("/join ")):
                    self.lobby.join(text[6:])
                elif text.startswith(("/topic ")):
                    self.lobby.setTopic(self.name, text[7:])
                elif text.startswith(("/msg ")):
                    blobs = text.split(" ")
                    self.lobby.sendMsg(blobs[1], " ".join(blobs[2:]))
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
        self.chatEdit.clear()
