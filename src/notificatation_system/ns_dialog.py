from PyQt4 import QtCore, QtGui
import util, time

"""
The UI popup of the notification system
"""
FormClass, BaseClass = util.loadUiType("notification_system/dialog.ui")
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
    def newEvent(self, pixmap, text, lifetime, sound):
        """ Called to display a new popup
        Keyword arguments:
        pixmap -- Icon for the event (displayed left)
        text- HTMl-Text of the vent (displayed right)
        lifetime -- Display duration
        sound -- true|false if should played
        """
        self.labelEvent.setText(str(text))
        if not pixmap:
            pixmap = self.standardIcon
        self.labelImage.setPixmap(pixmap)

        self.labelTime.setText(time.strftime("%H:%M:%S", time.gmtime()))
        QtCore.QTimer.singleShot(lifetime * 1000, self, QtCore.SLOT('hide()'))
        if sound:
            util.sound("chat/sfx/query.wav")
        self.show()

    @QtCore.pyqtSlot()
    def hide(self):
        super(FormClass, self).hide()
        self.client.notificationSystem.dialogClosed()

    # mouseReleaseEvent sometimes not fired
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.hide()