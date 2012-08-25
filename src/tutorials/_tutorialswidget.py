from PyQt4 import QtCore, QtGui
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest
import util
import os
import fa
from tutorials.tutorialitem import TutorialItem, TutorialItemDelegate

from tutorials import logger

FormClass, BaseClass = util.loadUiType("tutorials/tutorials.ui")


class tutorialsWidget(FormClass, BaseClass):
    def __init__(self, client, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)        
        
        self.setupUi(self)

        self.client = client
        self.client.tutorialsTab.layout().addWidget(self)    
        
        self.sections = {}
        self.tutorials = {}

        self.client.tutorialsInfo.connect(self.processTutorialInfo)
        
        
    def finishReplay(self, reply):
        filename = os.path.join(util.CACHE_DIR, str("tutorial.fafreplay"))
        replay  = QtCore.QFile(filename)
        replay.open(QtCore.QIODevice.WriteOnly | QtCore.QIODevice.Text)
        replay.write(reply.readAll())
        replay.close()
    
        fa.exe.replay(filename, True)
    
    def tutorialClicked(self, item):

        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.finishReplay)
        self.nam.get(QNetworkRequest(QtCore.QUrl(item.url)))            

    
    def processTutorialInfo(self, message):
        '''
        Two type here : section or tutorials.
        Sections are defining the differents type of tutorials
        '''
        
        if "section" in message :
            section = message["section"]
            desc = message["description"]
            
            group = QtGui.QGroupBox(self)


            group.setFont(QtGui.QFont("Segoe UI", 12, QtGui.QFont.Bold))
            
            sizePolicy = QtGui.QSizePolicy()
            sizePolicy.setVerticalPolicy(QtGui.QSizePolicy.MinimumExpanding)
            sizePolicy.setHorizontalPolicy(QtGui.QSizePolicy.Preferred)
            group.setSizePolicy(sizePolicy)
            group.setTitle(section)
            
            
            vbox = QtGui.QVBoxLayout()
            group.setLayout(vbox)
            
            list = QtGui.QListWidget(group)
            
            
            
            list.setItemDelegate(TutorialItemDelegate(self))
            list.itemDoubleClicked.connect(self.tutorialClicked)
            list.setViewMode(0)
            text = QtGui.QLabel()
            text.setAlignment(QtCore.Qt.AlignTop)
            text.setText(desc)
            vbox.addWidget(text)
            vbox.addWidget(list)
            self.verticalLayoutScroll.addWidget(group)
            
            self.sections[section] = list
            
        elif "tutorial" in message :
            tutorial = message["tutorial"]
            section = message["tutorial_section"]
            
            if section in self.sections :
                self.tutorials[tutorial] = TutorialItem(tutorial)
                self.tutorials[tutorial].update(message)
                
                self.sections[section].addItem(self.tutorials[tutorial]) 
                self.sections[section].setMinimumHeight(self.sections[section].minimumHeight() + 115)
        