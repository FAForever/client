from PyQt4 import QtCore, QtGui

import util, time
from fa import maps
from games.gameitem import GameItemDelegate
from multiprocessing import Lock

FormClass, BaseClass = util.loadUiType("notification_system/dialog.ui")

class NotficationSystem():
    FRIEND_ONLINE = 'friend_comes_online'
    NEW_GAME = 'new_game'

    def __init__(self, client):
        self.client = client

        self.dialog = NotficationDialog(self.client)
        self.events = []
        self.disabled = True
        self.lock = Lock()

        self.user = util.icon("client/user.png", pix=True)

    def isDisabled(self):
        return self.disabled or not self.client.actionNsEnabled.isChecked()

    @QtCore.pyqtSlot()
    def on_event(self, eventType, data):
        if self.isDisabled():
            return
        self.events.append((eventType, data))
        if self.dialog.isHidden():
            self.showEvent()

    def showEvent(self):
        self.lock.acquire()
        event = self.events[0]
        del self.events[0]
        self.lock.release()

        eventType = event[0]
        data = event[1]
        pixmap = None
        text = str(data)
        if eventType == self.FRIEND_ONLINE:
            pixmap = self.user
            text = '<html>%s<br><font color="silver" size="-2">joined</font> %s</html>' % (data['user'], data['channel'])
        elif eventType == self.NEW_GAME:
            pixmap = maps.preview(data['mapname'], pixmap=True).scaled(80, 80)
            text = '<html>%s<br><font color="silver" size="-2">on</font> %s</html>' % (data['title'], maps.getDisplayName(data['mapname']))

        self.dialog.newEvent(pixmap, text)

    def dialogClosed(self):
        if self.events:
            self.showEvent()


class NotficationDialog(FormClass, BaseClass):
    def __init__(self, client, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)
        self.client = client

        self.labelIcon.setPixmap(util.icon("client/tray_icon.png", pix=True).scaled(32, 32))
        self.standardIcon = util.icon("client/comment.png", pix=True)

        screen = QtGui.QDesktopWidget().screenGeometry()
        dialog_size = self.geometry()

        # TODO: more positions
        # bottom right
        self.move(screen.width() - dialog_size.width(), screen.height() - dialog_size.height())

        # Frameless, always on top, steal no focus & no entry at the taskbar
        self.setWindowFlags(QtCore.Qt.ToolTip)

        # TODO: integrate into client.css
        #self.setStyleSheet(self.client.styleSheet())

    @QtCore.pyqtSlot()
    def newEvent(self, pixmap, text):
        self.labelEvent.setText(str(text))
        if not pixmap:
            pixmap = self.standardIcon
        self.labelImage.setPixmap(pixmap)

        self.labelTime.setText(time.strftime("%H:%M:%S", time.gmtime()))
        QtCore.QTimer.singleShot(5000, self, QtCore.SLOT('hide()'))
        if self.client.actionNsSound.isChecked():
            util.sound("chat/sfx/query.wav")
        self.show()

    @QtCore.pyqtSlot()
    def hide(self):
        super(FormClass, self).hide()
        self.client.notificationSystem.dialogClosed()
