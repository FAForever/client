from PyQt5 import QtCore, QtWidgets
import util
import time
from .ns_settings import NotificationPosition

"""
The UI popup of the notification system
"""
FormClass, BaseClass = util.THEME.loadUiType("notification_system/dialog.ui")


class NotificationDialog(FormClass, BaseClass):

    def __init__(self, client, settings, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)
        self.client = client

        self.labelIcon.setPixmap(util.THEME.icon("client/tray_icon.png", pix=True).scaled(32, 32))
        self.standardIcon = util.THEME.icon("client/comment.png", pix=True)

        self.settings = settings
        self.updatePosition()

        # Frameless, always on top, steal no focus & no entry at the taskbar
        self.setWindowFlags(QtCore.Qt.ToolTip)
        self.labelEvent.setOpenExternalLinks(True)

        self.baseHeight = 165
        self.baseWidth = 375

        # TODO: integrate into client.css
        # self.setStyleSheet(self.client.styleSheet())

    @QtCore.pyqtSlot()
    def newEvent(self, pixmap, text, lifetime, sound, height = None, width = None):
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
        QtCore.QTimer.singleShot(lifetime * 1000, self.hide)
        if sound:
            util.THEME.sound("chat/sfx/query.wav")
        self.setFixedHeight(height or self.baseHeight)
        self.setFixedWidth(width or self.baseWidth)

        self.updatePosition()
        self.show()

    @QtCore.pyqtSlot()
    def hide(self):
        super(FormClass, self).hide()
        # check for next event to show notification for
        self.client.notificationSystem.checkEvent()

    # mouseReleaseEvent sometimes not fired
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.hide()

    def updatePosition(self):
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        dialog_size = self.geometry()
        position = self.settings.popup_position  # self.client.notificationSystem.settings.popup_position

        if position == NotificationPosition.TOP_LEFT:
            self.move(0, 0)
        elif position == NotificationPosition.TOP_RIGHT:
            self.move(screen.width() - dialog_size.width(), 0)
        elif position == NotificationPosition.BOTTOM_LEFT:
            self.move(0, screen.height() - dialog_size.height())
        else:
            self.move(screen.width() - dialog_size.width(), screen.height() - dialog_size.height())
