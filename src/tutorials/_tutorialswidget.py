from PyQt5 import QtCore, QtWidgets
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from fa.replay import replay
import util
import os
import fa
from tutorials.tutorialitem import TutorialItem, TutorialItemDelegate

import logging
logger = logging.getLogger(__name__)

FormClass, BaseClass = util.loadUiType("tutorials/tutorials.ui")


class tutorialsWidget(FormClass, BaseClass):
    def __init__(self, client, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)        
        
        self.setupUi(self)

        self.client = client
        self.client.tutorialsTab.layout().addWidget(self)    
        
        self.sections = {}
        self.tutorials = {}

        self.client.lobby_info.tutorialsInfo.connect(self.processTutorialInfo)
        
        logger.info("Tutorials instantiated.")
        
        
    def finishReplay(self, reply):
        if reply.error() != QNetworkReply.NoError:
            QtWidgets.QMessageBox.warning(self, "Network Error", reply.errorString())
        else:
            filename = os.path.join(util.CACHE_DIR, str("tutorial.fafreplay"))
            replay  = QtCore.QFile(filename)
            replay.open(QtCore.QIODevice.WriteOnly | QtCore.QIODevice.Text)
            replay.write(reply.readAll())
            replay.close()
    
            fa.replay(filename, True)
    
    def tutorialClicked(self, item):

        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.finishReplay)
        self.nam.get(QNetworkRequest(QtCore.QUrl(item.url)))            

    
    def processTutorialInfo(self, message):
        '''
        Two type here : section or tutorials.
        Sections are defining the differents type of tutorials
        '''
        
        logger.debug("Processing TutorialInfo")
        
        if "section" in message :
            section = message["section"]
            desc = message["description"]

            area = util.loadUi("tutorials/tutorialarea.ui")
            tabIndex = self.addTab(area, section)      
            self.setTabToolTip(tabIndex, desc)

            # Set up the List that contains the tutorial items
            area.listWidget.setItemDelegate(TutorialItemDelegate(self))
            area.listWidget.itemDoubleClicked.connect(self.tutorialClicked)
            
            self.sections[section] = area.listWidget
            
        elif "tutorial" in message :
            tutorial = message["tutorial"]
            section = message["tutorial_section"]
            
            if section in self.sections :
                self.tutorials[tutorial] = TutorialItem(tutorial)
                self.tutorials[tutorial].update(message, self.client)
                
                self.sections[section].addItem(self.tutorials[tutorial]) 
        
