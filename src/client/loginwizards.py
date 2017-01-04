from PyQt4 import QtCore, QtGui
import re
from config import Settings
import util

import hashlib
from client import ClientState
from config import modules as cfg


class LoginWizard(QtGui.QWizard):
    def __init__(self, client):
        QtGui.QWizard.__init__(self)

        self.client = client
        self.password = cfg.user.password.get()
        
        self.addPage(loginPage(self))

        self.setWizardStyle(QtGui.QWizard.ModernStyle)
        self.setModal(True)

        buttons_layout = [
            QtGui.QWizard.CancelButton,
            QtGui.QWizard.FinishButton
        ]

        self.setButtonLayout(buttons_layout)
        self.setWindowTitle("Login")
        self.accepted.connect(self.on_accepted)
        self.rejected.connect(self.on_rejected)

    @QtCore.pyqtSlot()
    def on_accepted(self):
        if (self.field("password") != "!!!password!!!"): #Not entirely nicely coded, this can go into a lambda function connected to the LineEdit
            self.password = hashlib.sha256(self.field("password").strip().encode("utf-8")).hexdigest()

        remember = self.field("remember")
        cfg.user.remember.set(remember)
        cfg.user.login.set(self.field("login").strip(), persist = remember)
        cfg.user.password.set(self.password, persist = remember) # This is the hash, not the dummy password

    @QtCore.pyqtSlot()
    def on_rejected(self):
        pass


class loginPage(QtGui.QWizardPage):
    def __init__(self, parent=None, *args, **kwargs):
        QtGui.QWizardPage.__init__(self, *args, **kwargs)

        self.parent= parent
        self.client = parent.client
        
        self.setButtonText(QtGui.QWizard.CancelButton, "Quit")
        self.setButtonText(QtGui.QWizard.FinishButton, "Login")        
        
        self.setTitle("ACU ready for combat.")
        self.setSubTitle("Log yourself in, commander.")
        
        self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("client/login_watermark.png"))

        loginLabel = QtGui.QLabel("&User name :")
        self.loginLineEdit = QtGui.QLineEdit()
        loginLabel.setBuddy(self.loginLineEdit)
        self.loginLineEdit.setText(cfg.user.login.get())

        passwordLabel = QtGui.QLabel("&Password :")
        self.passwordLineEdit = QtGui.QLineEdit()
        
        passwordLabel.setBuddy(self.passwordLineEdit)
        
        self.passwordLineEdit.setEchoMode(QtGui.QLineEdit.Password)
                
        if (cfg.user.password.get()):
            self.passwordLineEdit.setText("!!!password!!!")

        self.passwordLineEdit.selectionChanged.connect(self.passwordLineEdit.clear)               


        self.rememberCheckBox = QtGui.QCheckBox("&Remember me")
        self.rememberCheckBox.setChecked(cfg.user.remember.get())
        

        self.rememberCheckBox.clicked.connect(self.rememberCheck)

        self.createAccountBtn = QtGui.QPushButton("Create new Account")
        self.renameAccountBtn = QtGui.QPushButton("Rename your account")
        self.linkAccountBtn = QtGui.QPushButton("Link your account to Steam")
        self.forgotPasswordBtn = QtGui.QPushButton("Forgot Login or Password")
        self.reportBugBtn = QtGui.QPushButton("Report a Bug")

        self.createAccountBtn.released.connect(self.createAccount)
        self.renameAccountBtn.released.connect(self.renameAccount)
        self.linkAccountBtn.released.connect(self.linkAccount)
        self.forgotPasswordBtn.released.connect(self.forgotPassword)
        self.reportBugBtn.released.connect(self.reportBug)

        self.registerField('login', self.loginLineEdit)
        self.registerField('password', self.passwordLineEdit)
        self.registerField('remember', self.rememberCheckBox)


        layout = QtGui.QGridLayout()

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
        cfg.user.remember.set(self.rememberCheckBox.isChecked())

    @QtCore.pyqtSlot()
    def createAccount(self):
        wizard = creationAccountWizard(self)
        if wizard.exec_():
            #Re-load credentials after successful creation.
            self.loginLineEdit.setText(cfg.user.login.get())
            self.setField('password', "!!!password!!!")
            self.parent.password = cfg.user.password.get() # This is needed because we're writing the field in accept()

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

class creationAccountWizard(QtGui.QWizard):
    def __init__(self, parent=None):
        
        super(creationAccountWizard, self).__init__(parent)

        self.client = parent.client

        self.setOption(QtGui.QWizard.DisabledBackButtonOnLastPage)
        self.addPage(IntroPage())
        self.addPage(AccountCreationPage(self))
        self.addPage(AccountCreated())


        self.setWizardStyle(QtGui.QWizard.ModernStyle)

        self.setPixmap(QtGui.QWizard.BannerPixmap,
                QtGui.QPixmap('client/banner.png'))
        self.setPixmap(QtGui.QWizard.BackgroundPixmap,
                QtGui.QPixmap('client/background.png'))

        self.setWindowTitle("Create Account")



class gameSettingsWizard(QtGui.QWizard):
    def __init__(self, client, *args, **kwargs):
        QtGui.QWizard.__init__(self, *args, **kwargs)
        
        self.client = client

        self.settings = GameSettings()
        self.settings.gamePortSpin.setValue(cfg.game.port.get())
        self.settings.checkUPnP.setChecked(cfg.game.upnp.get())
        self.addPage(self.settings)

        self.setWizardStyle(1)

        self.setPixmap(QtGui.QWizard.BannerPixmap,
                QtGui.QPixmap('client/banner.png'))
        self.setPixmap(QtGui.QWizard.BackgroundPixmap,
                QtGui.QPixmap('client/background.png'))

        self.setWindowTitle("Set Game Port")

    def accept(self):
        cfg.game.port.set(self.settings.gamePortSpin.value())
        cfg.game.upnp.set(self.settings.checkUPnP.isChecked())
        QtGui.QWizard.accept(self)


class mumbleOptionsWizard(QtGui.QWizard):
    def __init__(self, client, *args, **kwargs):
        QtGui.QWizard.__init__(self, *args, **kwargs)
        
        self.client = client

        self.settings = MumbleSettings()
        self.settings.checkEnableMumble.setChecked(self.client.enableMumble)
        self.addPage(self.settings)

        self.setWizardStyle(1)

        self.setPixmap(QtGui.QWizard.BannerPixmap,
                QtGui.QPixmap('client/banner.png'))
        self.setPixmap(QtGui.QWizard.BackgroundPixmap,
                QtGui.QPixmap('client/background.png'))

        self.setWindowTitle("Configure Voice")

    def accept(self):
        self.client.enableMumble = self.settings.checkEnableMumble.isChecked()
        self.client.saveMumble()
        QtGui.QWizard.accept(self)

class IntroPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(IntroPage, self).__init__(parent)

        self.setTitle("Welcome to FA Forever.")
        self.setSubTitle("In order to play, you first need to create an account.")
        self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("client/account_watermark_intro.png"))

        label = QtGui.QLabel("This wizard will help you in the process of account creation.<br/><br/><b>At this time, we only allow one account per computer.</b>")
        
        label.setWordWrap(True)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)

class AccountCreationPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(AccountCreationPage, self).__init__(parent)

        self.parent = parent
        self.client = parent.client
        
        self.setTitle("Account Creation")
        self.setSubTitle("Please enter your desired login and password. Note that your password will not be stored on our server. Please specify a working email address in case you need to change it.")
        
        self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("client/account_watermark_input.png"))

        loginLabel = QtGui.QLabel("&User name :")
        self.loginLineEdit = QtGui.QLineEdit()
        rxLog = QtCore.QRegExp("[A-Z,a-z]{1}[A-Z,a-z,0-9,_,-]{0,15}")
        validLog = QtGui.QRegExpValidator(rxLog, self)
        self.loginLineEdit.setValidator(validLog)
        loginLabel.setBuddy(self.loginLineEdit)

        passwordLabel = QtGui.QLabel("&Password :")
        self.passwordLineEdit = QtGui.QLineEdit()
        passwordLabel.setBuddy(self.passwordLineEdit)

        self.passwordLineEdit.setEchoMode(2)

        passwordCheckLabel = QtGui.QLabel("&Re-type Password :")
        self.passwordCheckLineEdit = QtGui.QLineEdit()
        passwordCheckLabel.setBuddy(self.passwordCheckLineEdit)

        self.passwordCheckLineEdit.setEchoMode(2)

        EmailLabel = QtGui.QLabel("E-mail :")
        self.EmailLineEdit = QtGui.QLineEdit()
        rxMail = QtCore.QRegExp("^[a-zA-Z0-9]{1}[a-zA-Z0-9._%-]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,6}$")
        validMail = QtGui.QRegExpValidator(rxMail, self)
        self.EmailLineEdit.setValidator(validMail)

        self.registerField('login*', self.loginLineEdit)
        self.registerField('password*', self.passwordLineEdit)
        self.registerField('passwordCheck*', self.passwordCheckLineEdit)
        self.registerField('email*', self.EmailLineEdit)

        layout = QtGui.QGridLayout()
                
        layout.addWidget(loginLabel, 1, 0)
        layout.addWidget(self.loginLineEdit, 1, 1)
        
        layout.addWidget(passwordLabel, 2, 0)
        layout.addWidget(self.passwordLineEdit, 2, 1)
        
        layout.addWidget(passwordCheckLabel, 3, 0)
        layout.addWidget(self.passwordCheckLineEdit, 3, 1)
        
        layout.addWidget(EmailLabel, 4, 0)
        layout.addWidget(self.EmailLineEdit, 4, 1)

        self.setLayout(layout)
#

    def validateEmail(self, email):
        return re.match("^[a-zA-Z0-9._%-]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,6}$", email) is not None

    def validatePage(self):
        password = self.passwordLineEdit.text().encode("utf-8")
        confim_password = self.passwordCheckLineEdit.text().encode("utf-8")

        if password != confim_password:
            QtGui.QMessageBox.information(self, "Create account","Passwords don't match!")
            return False

        # Hashing the password client-side is not an effective way of ensuring security, but now we
        # have a database full of sha256(password) we have to start considering sha256(password) to
        # _be_ the user's password, and enforce a saner policy atop this.
        #
        # Soon. We promise. Hopefully before large scale identity theft takes place.
        hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
        
        email = self.EmailLineEdit.text()
        
        if not self.validateEmail(email) :
            QtGui.QMessageBox.information(self, "Create account", "Invalid Email address!")
            return False   

        login = self.loginLineEdit.text().strip()
        self.client.send({
            "command": "create_account",
            "login": login,
            "email": email,
            "password": hashed_password
        })

        # Wait for client state to change.
        util.wait(lambda: self.client.auth_state == ClientState.CREATED or self.client.auth_state == ClientState.REJECTED)
                
        if self.client.auth_state == ClientState.REJECTED:
            QtGui.QMessageBox.information(self, "Create account", "Sorry, this Login is not available, or the email address was already used.")
            return False
        elif self.client.auth_state == ClientState.CREATED:
            cfg.user.login.set(login, persist = cfg.user.remember.get())
            cfg.user.password.set(hashed_password, persist = cfg.user.remember.get())
            return True
        else:
            return False

class GameSettings(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(GameSettings, self).__init__(parent)

        self.parent = parent
        self.setTitle("Network Settings")
        self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("client/settings_watermark.png"))
        
        self.label = QtGui.QLabel()
        self.label.setText('Forged Alliance needs an open UDP port to play. If you have trouble connecting to other players, try the UPnP option first. If that fails, you should try to open or forward the port on your router and firewall.<br/><br/>Visit the <a href="http://forums.faforever.com/forums/viewforum.php?f=3">Tech Support Forum</a> if you need help.<br/><br/>')
        self.label.setOpenExternalLinks(True)
        self.label.setWordWrap(True)

        self.labelport = QtGui.QLabel()
        self.labelport.setText("<b>UDP Port</b> (default 6112)")
        self.labelport.setWordWrap(True)
        
        self.gamePortSpin = QtGui.QSpinBox() 
        self.gamePortSpin.setMinimum(1024)
        self.gamePortSpin.setMaximum(65535) 
        self.gamePortSpin.setValue(6112)

        self.checkUPnP = QtGui.QCheckBox("use UPnP")
        self.checkUPnP.setToolTip("FAF can try to open and forward your game port automatically using UPnP.<br/><b>Caution: This doesn't work for all connections, but may help with some routers.</b>")

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.labelport)
        layout.addWidget(self.gamePortSpin)
        layout.addWidget(self.checkUPnP)
        self.setLayout(layout)


    def validatePage(self):        
        return 1

class MumbleSettings(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(MumbleSettings, self).__init__(parent)

        self.parent = parent
        self.setTitle("Voice Settings")
        self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("client/settings_watermark.png"))
        
        self.label = QtGui.QLabel()
        self.label.setText('FAF supports the automatic setup of voice connections between you and your team mates. It will automatically move you into a channel with your team mates anytime you enter a game lobby or start a game. To enable, download and install <a href="http://mumble.sourceforge.net/">Mumble</a> and tick the checkbox below.')
        self.label.setOpenExternalLinks(True)
        self.label.setWordWrap(True)

        self.checkEnableMumble = QtGui.QCheckBox("Enable Mumble Connector")

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.checkEnableMumble)
        self.setLayout(layout)

    def validatePage(self):        
        return 1



class AccountCreated(QtGui.QWizardPage):
    def __init__(self, *args, **kwargs):
        QtGui.QWizardPage.__init__(self, *args, **kwargs)

        self.setFinalPage(True)
        self.setTitle("Congratulations!")
        self.setSubTitle("Your Account has been created.")
        self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("client/account_watermark_created.png"))

        self.label = QtGui.QLabel()
        self.label.setWordWrap(True)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def initializePage(self):
        self.label.setText("You will be redirected to the login page.")

