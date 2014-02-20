from PyQt4 import QtCore, QtGui

import util, time

FormClass, BaseClass = util.loadUiType("notification_system/dialog.ui")

class NotficationSystem():
    def __init__(self, client):
        self.client = client

        self.dialog = NotficationDialog(self.client)
        self.events = []


    @QtCore.pyqtSlot()
    def addEvent(self, text):
        if not self.client.actionNsEnabled.isChecked():
            return
        self.events.append(text)
        if self.dialog.isHidden():
            self.showEvent()

    def showEvent(self):
        self.dialog.newEvent(self.events[0])
        del self.events[0]
        self.dialog.show()

    def dialogClosed(self):
        if self.events:
            self.showEvent()


class NotficationDialog(FormClass, BaseClass):
    def __init__(self, client, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)
        self.client = client

        self.labelIcon.setPixmap(util.icon("client/tray_icon.png", pix=True).scaled(32, 32))

        screen = QtGui.QDesktopWidget().screenGeometry()
        dialog_size = self.geometry()

        # TODO: more positions
        # bottom right
        self.move(screen.width() - dialog_size.width(), screen.height() - dialog_size.height())

        # Frameless
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowMinimizeButtonHint)

        #self.setStyleSheet(self.client.styleSheet())

    @QtCore.pyqtSlot()
    def newEvent(self, text):
        self.labelEvent.setText(text)
        self.labelTime.setText(time.strftime("%H:%M:%S", time.gmtime()))
        QtCore.QTimer.singleShot(3000, self, QtCore.SLOT('hide()'))
        if self.client.actionNsSound.isChecked():
            util.sound("chat/sfx/query.wav")

    @QtCore.pyqtSlot()
    def hide(self):
        super(FormClass, self).hide()
        self.client.notificationSystem.dialogClosed()
