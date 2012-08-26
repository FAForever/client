from PyQt4 import QtCore, QtGui
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest
import util

class avatarWidget(QtGui.QDialog):
    def __init__(self, parent, user, *args, **kwargs):
        
        QtGui.QDialog.__init__(self, *args, **kwargs)
        
        self.user = user
        self.parent = parent
        
        self.parent.requestAvatars()
        self.group_layout = QtGui.QVBoxLayout(self)
        
        
        self.parent.avatarList.connect(self.avatarList)
    
        self.nams = {}
        self.avatars = {}
        

    def finishRequest(self, reply):

        if reply.url().toString() in self.avatars :
            img = QtGui.QImage()
            img.loadFromData(reply.readAll())
            pix = QtGui.QPixmap(img)
            self.avatars[reply.url().toString()].setIcon(QtGui.QIcon(pix))   
            self.avatars[reply.url().toString()].setIconSize(pix.rect().size())     
        
            util.addrespix(reply.url().toString(), QtGui.QPixmap(img))
    
    def clicked(self):
        self.parent.addAvatar(self.user, None)
        self.close()
        
    def create_connect(self, x):
        return lambda: self.doit(x)
    
    def doit(self, val):
        self.parent.addAvatar(self.user, val)
        self.close()
    
    def avatarList(self, avatar_list):
        
        button = QtGui.QPushButton()
        self.group_layout.addWidget(button)
        self.avatars["None"] = button
        
        button.clicked.connect(self.clicked)
        
        for avatar in avatar_list :
            
            avatarPix = util.respix(avatar["url"])
            button = QtGui.QPushButton()
            button.clicked.connect(self.create_connect(avatar["url"]))
            self.group_layout.addWidget(button)
            button.setToolTip(avatar["tooltip"])
            url = QtCore.QUrl(avatar["url"])            
            self.avatars[avatar["url"]] = button
            
            if not avatarPix :          
                self.nams[url] = QNetworkAccessManager(button)
                self.nams[url].finished.connect(self.finishRequest)
                self.nams[url].get(QNetworkRequest(url))
            else :
                self.avatars[avatar["url"]].setIcon(QtGui.QIcon(avatarPix))   
                self.avatars[avatar["url"]].setIconSize(avatarPix.rect().size())           

        
        
        