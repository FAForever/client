from PyQt4 import QtCore, QtGui, uic
import util

FormClass, BaseClass = uic.loadUiType("../res/client/login.ui")

class LoginWidget(FormClass, BaseClass): #TODO
    def __init__(self, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)
        self.setupUi(self)
        util.setStyleSheet(self, "client/login.css")
        self.splash.setPixmap(util.pixmap("client/login_watermark.png"))


    @QtCore.pyqtSlot()
    def on_accepted(self):
        print "Accepted!"

    @QtCore.pyqtSlot(bool)
    def on_remember_checked(self, checked):
        print "Checked {}".format(str(checked))

    @QtCore.pyqtSlot()
    def on_rejected(self):
        print "Rejected!"

    @QtCore.pyqtSlot()
    def on_new_account(self):
        print "New account!"

    @QtCore.pyqtSlot()
    def on_rename_account(self):
        print "Rename account!"

    @QtCore.pyqtSlot()
    def on_steamlink_account(self):
        print "Steamlink_account!"

    @QtCore.pyqtSlot()
    def on_forgot_password(self):
        print "Forgot password!"

    @QtCore.pyqtSlot()
    def on_bugreport(self):
        print "Bugreport!"
