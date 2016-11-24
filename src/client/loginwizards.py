from PyQt4 import QtCore, QtGui
import re
from config import Settings
import util

import hashlib

class LoginWizard(QtGui.QWizard):
    def __init__(self, client):
        QtGui.QWizard.__init__(self)

        self.client = client
        self.login = client.login
        self.password = client.password
        
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

        self.client.remember = self.field("remember")
        self.client.login = self.field("login").strip()
        self.client.password = self.password  # This is the hash, not the dummy password

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
        self.loginLineEdit.setText(self.client.login)

        passwordLabel = QtGui.QLabel("&Password :")
        self.passwordLineEdit = QtGui.QLineEdit()
        
        passwordLabel.setBuddy(self.passwordLineEdit)
        
        self.passwordLineEdit.setEchoMode(QtGui.QLineEdit.Password)
                
        if (self.client.password):
            self.passwordLineEdit.setText("!!!password!!!")

        self.passwordLineEdit.selectionChanged.connect(self.passwordLineEdit.clear)               


        self.rememberCheckBox = QtGui.QCheckBox("&Remember me")
        self.rememberCheckBox.setChecked(self.client.remember)
        

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


    def validatePage(self):        
        return 1
