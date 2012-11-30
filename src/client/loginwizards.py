#-------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------





from PyQt4 import QtCore, QtGui

import re
import util

import hashlib
from client import ClientState, logger

PASSWORD_RECOVERY_URL = "http://www.faforever.com/faf/forgotPass.php"

class LoginWizard(QtGui.QWizard):
    def __init__(self, client):
        QtGui.QWizard.__init__(self)

        self.client = client
        self.login = client.login
        self.password = client.password
        
        self.addPage(loginPage(self))

        self.setWizardStyle(QtGui.QWizard.ModernStyle)
        self.setModal(True)

        buttons_layout = []
        buttons_layout.append(QtGui.QWizard.CancelButton )
        buttons_layout.append(QtGui.QWizard.FinishButton )

        self.setButtonLayout(buttons_layout)

        self.setWindowTitle("Login")



    def accept(self):
        self.login = self.field("login")
        if (self.field("password") != "!!!password!!!"): #Not entirely nicely coded, this can go into a lambda function connected to the LineEdit                    
            self.password = hashlib.sha256(self.field("password").encode("utf-8")).hexdigest()

        self.client.login = self.field("login")
        self.client.password = self.password    #this is the hash, not the dummy password
        self.client.remember = self.field("remember")
        self.client.autologin = self.field("autologin")
        
        QtGui.QWizard.accept(self)


    def reject(self):
        QtGui.QWizard.reject(self)


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


        self.rememberCheckBox = QtGui.QCheckBox("&Remember password")
        self.rememberCheckBox.setChecked(self.client.remember)
        
        self.autologinCheckBox = QtGui.QCheckBox("&Automatic Login")
        self.autologinCheckBox.setChecked(self.client.autologin)
        self.autologinCheckBox.setEnabled(self.client.remember)
        
        self.rememberCheckBox.clicked.connect(self.rememberCheck)
        self.rememberCheckBox.clicked.connect(self.autologinCheckBox.setChecked)
        self.rememberCheckBox.clicked.connect(self.autologinCheckBox.setEnabled)
        
        self.createAccountBtn = QtGui.QPushButton("Create new Account")
        self.forgotPasswordBtn = QtGui.QPushButton("Forgot Login or Password")
        self.reportBugBtn = QtGui.QPushButton("Report a Bug")

        self.createAccountBtn.released.connect(self.createAccount)
        self.forgotPasswordBtn.released.connect(self.forgotPassword)
        self.reportBugBtn.released.connect(self.reportBug)

        self.registerField('login', self.loginLineEdit)
        self.registerField('password', self.passwordLineEdit)
        self.registerField('remember', self.rememberCheckBox)
        self.registerField('autologin', self.autologinCheckBox)


        layout = QtGui.QGridLayout()

        layout.addWidget(loginLabel, 1, 0)
        layout.addWidget(self.loginLineEdit, 1, 1)
        
        layout.addWidget(passwordLabel, 2, 0)
        layout.addWidget(self.passwordLineEdit, 2, 1)

        layout.addWidget(self.rememberCheckBox, 3, 0, 1, 3)
        layout.addWidget(self.autologinCheckBox, 4, 0, 1, 3)
        layout.addWidget(self.createAccountBtn, 5, 0, 1, 3)
        layout.addWidget(self.forgotPasswordBtn, 6, 0, 1, 3)
        layout.addWidget(self.reportBugBtn, 8, 0, 1, 3)

        self.setLayout(layout)



    def rememberCheck(self):
        self.client.remember = self.rememberCheckBox.isChecked()
                
        
    @QtCore.pyqtSlot()
    def createAccount(self):
        wizard = creationAccountWizard(self)
        if wizard.exec_():
            #Re-load credentials after successful creation.
            self.loginLineEdit.setText(self.client.login)
            self.setField('password', "!!!password!!!")
            self.parent.password = self.client.password # This is needed because we're writing the field in accept()
        
        
    @QtCore.pyqtSlot()
    def forgotPassword(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(PASSWORD_RECOVERY_URL))


    @QtCore.pyqtSlot()
    def reportBug(self):
        util.ReportDialog().exec_()



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
        self.settings.gamePortSpin.setValue(self.client.gamePort)
        self.settings.checkUPnP.setChecked(self.client.useUPnP)
        self.addPage(self.settings)

        self.setWizardStyle(1)

        self.setPixmap(QtGui.QWizard.BannerPixmap,
                QtGui.QPixmap('client/banner.png'))
        self.setPixmap(QtGui.QWizard.BackgroundPixmap,
                QtGui.QPixmap('client/background.png'))

        self.setWindowTitle("Set Game Port")


    def accept(self):
        self.client.gamePort = self.settings.gamePortSpin.value()
        self.client.useUPnP = self.settings.checkUPnP.isChecked()
        self.client.savePort()
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

        self.password1 = ''
        self.password2 = ''
        
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
        if email.count("@") != 1:
            return False
        if len(email) > 6:
            if re.match("^[a-zA-Z0-9._%-]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,6}$", email) != None:
                return True
        return False


    def validatePage(self):
        password1 = hashlib.sha256(self.passwordLineEdit.text().encode("utf-8")).hexdigest()        
        password2 = hashlib.sha256(self.passwordCheckLineEdit.text().encode("utf-8")).hexdigest()
        
        if password1 != password2 :
            QtGui.QMessageBox.information(self, "Create account","Passwords don't match!")
            return False
        
        email = self.EmailLineEdit.text()
        
        if not self.validateEmail(email) :
            QtGui.QMessageBox.information(self, "Create account", "Invalid Email address!")
            return False   
        
        # check if the login is okay
        login = self.loginLineEdit.text()
        
        self.client.loginWriteToFaServer("CREATE_ACCOUNT", login, email, password1)

        # Wait for client state to change.
        util.wait(lambda: self.client.state)
                
        if self.client.state == ClientState.REJECTED:
            QtGui.QMessageBox.information(self, "Create account", "Sorry, this Login is not available, or the email address was already used.")
            return False
        else:
            self.client.login = login
            self.client.password = password1
            return True  


class GameSettings(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(GameSettings, self).__init__(parent)

        self.parent = parent
        self.setTitle("Network Settings")
        self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("client/settings_watermark.png"))
        
        self.label = QtGui.QLabel()
        self.label.setText('Forged Alliance needs an open UDP port to play. If you have trouble connecting to other players, try the UPnP option first. If that fails, you should try to open or forward the port on your router and firewall.<br/><br/>Visit the <a href="http://www.faforever.com/forums/viewforum.php?f=3">Tech Support Forum</a> if you need help.<br/><br/>')
        self.label.setOpenExternalLinks(True)
        self.label.setWordWrap(True)

        self.labelport = QtGui.QLabel()
        self.labelport.setText("<b>UDP Port</b> (default 6112)")
        self.labelport.setWordWrap(True)
        
        self.gamePortSpin = QtGui.QSpinBox() 
        self.gamePortSpin.setMinimum(10)
        self.gamePortSpin.setMaximum(50000) 
        self.gamePortSpin.setValue(6112)

        self.checkUPnP = QtGui.QCheckBox("use UPnP (experimental)")
        self.checkUPnP.setToolTip("FAF can try to open and forward your game port automatically using UPnP.<br/><b>Caution: This doesn't work for all connections, but may help with some routers.</b>")

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.labelport)
        layout.addWidget(self.gamePortSpin)
        layout.addWidget(self.checkUPnP)
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

