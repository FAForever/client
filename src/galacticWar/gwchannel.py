from PyQt4 import QtGui, QtCore
import util
from chat.channel import Channel
from chat.chatter import Chatter


    
class gwChannel(Channel):
    def __init__(self, lobby, name, private=True, *args, **kwargs):
        super(self.__class__, self).__init__(lobby, name)
        
    def setup(self):
        
        # Non-query channels have a sorted nicklist
        self.nickList.sortItems(Chatter.SORT_COLUMN)
        
        self.nickList.hide()
        self.nickFilter.hide()

        self.joinLabel.hide()
        self.channelsComboBox.hide()

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
            

        self.chatArea.anchorClicked.connect(self.openUrl)
        self.chatEdit.returnPressed.connect(self.sendLine)
        self.chatEdit.setChatters(self.chatters)
        self.lobby.client.doneresize.connect(self.resizing)

        self.resizeTimer = QtCore.QTimer(self)
        self.resizeTimer.timeout.connect(self.canresize)
        
        self.gwChannel = True
