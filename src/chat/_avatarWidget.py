from PyQt5 import QtCore
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import QDialog, QGridLayout, QPushButton, QVBoxLayout, QCheckBox, QGroupBox, \
                            QListWidget, QFileDialog, QInputDialog, QLineEdit, QMessageBox

from PyQt5.QtGui import QIcon, QPixmap, QImage

import base64, zlib, os
import util


class playerAvatar(QDialog):
    def __init__(self, users = [], idavatar = 0, parent=None, *args, **kwargs):
        QDialog.__init__(self, *args, **kwargs)
        
        self.parent = parent
        self.users = users
        self.checkBox = {}
        self.idavatar = idavatar
        
        self.setStyleSheet(self.parent.styleSheet())
        
        self.grid = QGridLayout(self)
        self.userlist = None
        #self.grid.addWidget(self.userlist, 0, 0)
        
        self.removeButton = QPushButton("&Remove users")
        self.grid.addWidget(self.removeButton,1,0)

        self.removeButton.clicked.connect(self.removeThem)
        
        self.setWindowTitle("Users using this avatar")
        self.resize(480, 320)         

    def processList(self, users, idavatar):
        self.checkBox = {}
        self.users = users
        self.idavatar = idavatar
        self.userlist = self.createUserSelection()
        self.grid.addWidget(self.userlist, 0, 0)
        #self.grid.addWidget()


    
    def removeThem(self):
        for user in self.checkBox :
            if self.checkBox[user].checkState() == 2 :
                self.parent.send(dict(command="admin", action="remove_avatar", iduser = user, idavatar = self.idavatar))
        self.close()
            

    def createUserSelection(self):
        groupBox = QGroupBox("Select the users you want to remove this avatar :")
        vbox = QVBoxLayout()
        
        for user in self.users :
            self.checkBox[user["iduser"]] = QCheckBox(user["login"])
            vbox.addWidget(self.checkBox[user["iduser"]])
        
        vbox.addStretch(1)
        groupBox.setLayout(vbox)

        return groupBox          
            

class avatarWidget(QDialog):
    def __init__(self, parent, user, personal = False, *args, **kwargs):

        QDialog.__init__(self, *args, **kwargs)

        self.user = user
        self.personal = personal
        self.parent = parent

        self.setStyleSheet(self.parent.styleSheet())
        self.setWindowTitle ( "Avatar manager")


        self.group_layout   = QVBoxLayout(self)
        self.listAvatars    = QListWidget()

        self.listAvatars.setWrapping(1)
        self.listAvatars.setSpacing(5)
        self.listAvatars.setResizeMode(1)

        self.group_layout.addWidget(self.listAvatars)

        if not self.personal :
            self.addAvatarButton = QPushButton("Add/Edit avatar")
            self.addAvatarButton.clicked.connect(self.addAvatar)
            self.group_layout.addWidget(self.addAvatarButton)

        self.item = []
        self.parent.avatarList.connect(self.avatarList)
        self.parent.playerAvatarList.connect(self.doPlayerAvatarList)

        self.playerList = playerAvatar(parent = self.parent)

        self.nams = {}
        self.avatars = {}

        self.finished.connect(self.cleaning)

    def showEvent(self, event):
        self.parent.requestAvatars(self.personal)


    def addAvatar(self):

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog

        fileName = QFileDialog.getOpenFileName(self,
                "Select the PNG file",
                "",
                "png Files (*.png)", options)
        if fileName:
            ## check the properties of that file
            pixmap = QPixmap(fileName)
            if pixmap.height() == 20 and pixmap.width() == 40 :

                text, ok = QInputDialog.getText(self, "Avatar description",
                "Please enter the tooltip :", QLineEdit.Normal, "")

                if ok and text != '':
                    file = QtCore.QFile(fileName)
                    file.open(QtCore.QIODevice.ReadOnly)
                    fileDatas = base64.b64encode(zlib.compress(file.readAll()))
                    file.close()

                    self.parent.send(dict(command="avatar", action="upload_avatar", name=os.path.basename(fileName),description=text, file=fileDatas))
            else:
                QMessageBox.warning(self, "Bad image", "The image must be in png, format is 40x20 !")

            #self.client.send(dict(command="edits", action="submit", file = fileDatas))

    def finishRequest(self, reply):

        if reply.url().toString() in self.avatars :
            img = QImage()
            img.loadFromData(reply.readAll())
            pix = QPixmap(img)
            self.avatars[reply.url().toString()].setIcon(QIcon(pix))
            self.avatars[reply.url().toString()].setIconSize(pix.rect().size())

            util.addrespix(reply.url().toString(), QPixmap(img))

    def clicked(self):
        self.doit(None)
        self.close()

    def create_connect(self, x):
        return lambda: self.doit(x)

    def doit(self, val):
        if self.personal == True :
            self.parent.send(dict(command="avatar", action="select", avatar=val))
            self.close()

        else :
            if self.user == None :
                self.parent.send(dict(command="admin", action="list_avatar_users", avatar=val))
            else :
                self.parent.send(dict(command="admin", action="add_avatar", user=self.user, avatar=val))
                self.close()


    def doPlayerAvatarList(self, message):
        self.playerList = playerAvatar(parent = self.parent)
        player_avatar_list  = message["player_avatar_list"]
        idavatar            = message["avatar_id"]
        self.playerList.processList(player_avatar_list, idavatar)
        self.playerList.show()

    def avatarList(self, avatar_list):
        self.listAvatars.clear()
        button = QtGui.QPushButton()
        #self.group_layout.addWidget(button)
        self.avatars["None"] = button

        item = QtGui.QListWidgetItem()
        item.setSizeHint (QtCore.QSize(40,20))

        self.item.append(item)

        self.listAvatars.addItem (item )
        self.listAvatars.setItemWidget ( item, button )

        button.clicked.connect(self.clicked)

        for avatar in avatar_list :

            avatarPix = util.respix(avatar["url"])
            button = QtGui.QPushButton()

            button.clicked.connect(self.create_connect(avatar["url"]))

            item = QtGui.QListWidgetItem()
            item.setSizeHint (QtCore.QSize(40,20))
            self.item.append(item)

            self.listAvatars.addItem (item )


            button.setToolTip(avatar["tooltip"])
            url = QtCore.QUrl(avatar["url"])
            self.avatars[avatar["url"]] = button

            self.listAvatars.setItemWidget ( item, self.avatars[avatar["url"]] )

            if not avatarPix :
                self.nams[url] = QNetworkAccessManager(button)
                self.nams[url].finished.connect(self.finishRequest)
                self.nams[url].get(QNetworkRequest(url))
            else :
                self.avatars[avatar["url"]].setIcon(QtGui.QIcon(avatarPix))
                self.avatars[avatar["url"]].setIconSize(avatarPix.rect().size())

    def cleaning(self):
        if self != self.parent.avatarAdmin:
            self.parent.avatarList.disconnect(self.avatarList)
            self.parent.playerAvatarList.disconnect(self.doPlayerAvatarList)
