from PyQt5 import QtCore, QtWidgets, QtGui
import re
from config import Settings
import util

import hashlib

class LoginWizard(QtWidgets.QWizard):
    def __init__(self, client):
        QtWidgets.QWizard.__init__(self)

        self.client = client
        self.login = client.login
        self.password = client.password
        
        self.addPage(loginPage(self))

        self.setWizardStyle(QtWidgets.QWizard.ModernStyle)
        self.setModal(True)

        buttons_layout = [
            QtWidgets.QWizard.CancelButton,
            QtWidgets.QWizard.FinishButton
        ]

        self.setButtonLayout(buttons_layout)
        self.setWindowTitle("Login")
        self.accepted.connect(self.on_accepted)
        self.rejected.connect(self.on_rejected)

    @QtCore.pyqtSlot()
    def on_accepted(self):
        if (self.field("password") != "!!!password!!!"): #Not entirely nicely coded, this can go into a lambda function connected to the LineEdit
            self.password = hashlib.sha256(self.field("password").strip().encode("utf-8")).hexdigest()

        self.client.remember = self.field("remember")
        self.client.login = self.field("login").strip()
        self.client.password = self.password  # This is the hash, not the dummy password

    @QtCore.pyqtSlot()
    def on_rejected(self):
        pass


class loginPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None, *args, **kwargs):
        QtWidgets.QWizardPage.__init__(self, *args, **kwargs)

        self.parent= parent
        self.client = parent.client
        
        self.setButtonText(QtWidgets.QWizard.CancelButton, "Quit")
        self.setButtonText(QtWidgets.QWizard.FinishButton, "Login")
        
        self.setTitle("ACU ready for combat.")
        self.setSubTitle("Log yourself in, commander.")
        
        self.setPixmap(QtWidgets.QWizard.WatermarkPixmap, util.pixmap("client/login_watermark.png"))

        loginLabel = QtWidgets.QLabel("&User name :")
        self.loginLineEdit = QtWidgets.QLineEdit()
        loginLabel.setBuddy(self.loginLineEdit)
        self.loginLineEdit.setText(self.client.login)

        passwordLabel = QtWidgets.QLabel("&Password :")
        self.passwordLineEdit = QtWidgets.QLineEdit()
        
        passwordLabel.setBuddy(self.passwordLineEdit)
        
        self.passwordLineEdit.setEchoMode(QtWidgets.QLineEdit.Password)
                
        if (self.client.password):
            self.passwordLineEdit.setText("!!!password!!!")

        self.passwordLineEdit.selectionChanged.connect(self.passwordLineEdit.clear)               


        self.rememberCheckBox = QtWidgets.QCheckBox("&Remember me")
        self.rememberCheckBox.setChecked(self.client.remember)
        

        self.rememberCheckBox.clicked.connect(self.rememberCheck)

        self.createAccountBtn = QtWidgets.QPushButton("Create new Account")
        self.renameAccountBtn = QtWidgets.QPushButton("Rename your account")
        self.linkAccountBtn = QtWidgets.QPushButton("Link your account to Steam")
        self.forgotPasswordBtn = QtWidgets.QPushButton("Forgot Login or Password")
        self.reportBugBtn = QtWidgets.QPushButton("Report a Bug")

        self.createAccountBtn.released.connect(self.createAccount)
        self.renameAccountBtn.released.connect(self.renameAccount)
        self.linkAccountBtn.released.connect(self.linkAccount)
        self.forgotPasswordBtn.released.connect(self.forgotPassword)
        self.reportBugBtn.released.connect(self.reportBug)

        self.registerField('login', self.loginLineEdit)
        self.registerField('password', self.passwordLineEdit)
        self.registerField('remember', self.rememberCheckBox)


        layout = QtWidgets.QGridLayout()

        layout.addWidget(loginLabel, 1, 0)
        layout.addWidget(self.loginLineEdit, 1, 1)
        
        layout.addWidget(passwordLabel, 2, 0)
        layout.addWidget(self.passwordLineEdit, 2, 1)

        layout.addWidget(self.rememberCheckBox, 3, 0, 1, 3)
        layout.addWidget(self.createAccountBtn, 5, 0, 1, 3)
        layout.addWidget(self.renameAccountBtn, 6, 0, 1, 3)
        layout.addWidget(self.linkAccountBtn, 7, 0, 1, 3)
        layout.addWidget(self.forgotPasswordBtn, 8, 0, 1, 3)

        layout.addWidget(self.reportBugBtn, 10, 0, 1, 3)

        self.setLayout(layout)

    def rememberCheck(self):
        self.client.remember = self.rememberCheckBox.isChecked()

    @QtCore.pyqtSlot()
    def createAccount(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(Settings.get("CREATE_ACCOUNT_URL")))

    @QtCore.pyqtSlot()
    def linkAccount(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(Settings.get("STEAMLINK_URL")))

    @QtCore.pyqtSlot()
    def renameAccount(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(Settings.get("NAME_CHANGE_URL")))

    @QtCore.pyqtSlot()
    def forgotPassword(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(Settings.get("PASSWORD_RECOVERY_URL")))

    @QtCore.pyqtSlot()
    def reportBug(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(Settings.get("TICKET_URL")))


class gameSettingsWizard(QtWidgets.QWizard):
    def __init__(self, client, *args, **kwargs):
        QtWidgets.QWizard.__init__(self, *args, **kwargs)
        
        self.client = client

        self.settings = GameSettings()
        self.settings.gamePortSpin.setValue(self.client.gamePort)
        self.settings.checkUPnP.setChecked(self.client.useUPnP)
        self.addPage(self.settings)

        self.setWizardStyle(1)

        self.setPixmap(QtWidgets.QWizard.BannerPixmap,
                QtGui.QPixmap('client/banner.png'))
        self.setPixmap(QtWidgets.QWizard.BackgroundPixmap,
                       QtGui.QPixmap('client/background.png'))

        self.setWindowTitle("Set Game Port")

    def accept(self):
        self.client.gamePort = self.settings.gamePortSpin.value()
        self.client.useUPnP = self.settings.checkUPnP.isChecked()
        QtWidgets.QWizard.accept(self)


class mumbleOptionsWizard(QtWidgets.QWizard):
    def __init__(self, client, *args, **kwargs):
        QtWidgets.QWizard.__init__(self, *args, **kwargs)
        
        self.client = client

        self.settings = MumbleSettings()
        self.settings.checkEnableMumble.setChecked(self.client.enableMumble)
        self.addPage(self.settings)

        self.setWizardStyle(1)

        self.setPixmap(QtWidgets.QWizard.BannerPixmap,
                QtWidgets.QPixmap('client/banner.png'))
        self.setPixmap(QtWidgets.QWizard.BackgroundPixmap,
                QtWidgets.QPixmap('client/background.png'))

        self.setWindowTitle("Configure Voice")

    def accept(self):
        self.client.enableMumble = self.settings.checkEnableMumble.isChecked()
        self.client.saveMumble()
        QtWidgets.QWizard.accept(self)

class GameSettings(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super(GameSettings, self).__init__(parent)

        self.parent = parent
        self.setTitle("Network Settings")
        self.setPixmap(QtWidgets.QWizard.WatermarkPixmap, util.pixmap("client/settings_watermark.png"))
        
        self.label = QtWidgets.QLabel()
        self.label.setText('Forged Alliance needs an open UDP port to play. If you have trouble connecting to other players, try the UPnP option first. If that fails, you should try to open or forward the port on your router and firewall.<br/><br/>Visit the <a href="http://forums.faforever.com/forums/viewforum.php?f=3">Tech Support Forum</a> if you need help.<br/><br/>')
        self.label.setOpenExternalLinks(True)
        self.label.setWordWrap(True)

        self.labelport = QtWidgets.QLabel()
        self.labelport.setText("<b>UDP Port</b> (default 6112)")
        self.labelport.setWordWrap(True)
        
        self.gamePortSpin = QtWidgets.QSpinBox()
        self.gamePortSpin.setMinimum(1024)
        self.gamePortSpin.setMaximum(65535) 
        self.gamePortSpin.setValue(6112)

        self.checkUPnP = QtWidgets.QCheckBox("use UPnP")
        self.checkUPnP.setToolTip("FAF can try to open and forward your game port automatically using UPnP.<br/><b>Caution: This doesn't work for all connections, but may help with some routers.</b>")

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.labelport)
        layout.addWidget(self.gamePortSpin)
        layout.addWidget(self.checkUPnP)
        self.setLayout(layout)


    def validatePage(self):        
        return 1

class MumbleSettings(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super(MumbleSettings, self).__init__(parent)

        self.parent = parent
        self.setTitle("Voice Settings")
        self.setPixmap(QtWidgets.QWizard.WatermarkPixmap, util.pixmap("client/settings_watermark.png"))
        
        self.label = QtWidgets.QLabel()
        self.label.setText('FAF supports the automatic setup of voice connections between you and your team mates. It will automatically move you into a channel with your team mates anytime you enter a game lobby or start a game. To enable, download and install <a href="http://mumble.sourceforge.net/">Mumble</a> and tick the checkbox below.')
        self.label.setOpenExternalLinks(True)
        self.label.setWordWrap(True)

        self.checkEnableMumble = QtWidgets.QCheckBox("Enable Mumble Connector")

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.checkEnableMumble)
        self.setLayout(layout)

    def validatePage(self):        
        return 1
