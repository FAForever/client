from PyQt4 import QtCore, QtGui

import util, time
from fa import maps
from games.gameitem import GameItemDelegate
from multiprocessing import Lock

class NotficationSystem():
    FRIEND_ONLINE = 'friend_comes_online'
    NEW_GAME = 'new_game'

    def __init__(self, client):
        self.client = client

        self.dialog = NotficationDialog(self.client)
        self.events = []
        self.disabledStartup = True
        self.lock = Lock()

        self.settings = NsSettingsDialog(self.client)

        self.user = util.icon("client/user.png", pix=True)

    def isDisabled(self):
        return self.disabledStartup or not self.settings.enabled

    def setNotificationEnabled(self, enabled):
        self.settings.enabled = enabled
        self.settings.saveSettings()

    @QtCore.pyqtSlot()
    def on_event(self, eventType, data):
        if self.isDisabled():
            return
        self.events.append((eventType, data))
        if self.dialog.isHidden():
            self.showEvent()

    @QtCore.pyqtSlot()
    def on_showSettings(self):
        self.settings.show()

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

            #TODO: outsource as function?
            mod = None if 'featured_mod' not in data else data['featured_mod']
            mods = None if 'sim_mods' not in data else data['sim_mods']

            modstr = ''
            if (mod != 'faf' or mods):
                modstr = mod
                if mods:
                    if mod == 'faf':modstr = ", ".join(mods.values())
                    else: modstr = mod + " & " + ", ".join(mods.values())
                    if len(modstr) > 20: modstr = modstr[:15] + "..."

            modhtml = '' if (modstr == '') else '<br><font size="-4"><font color="red">mods</font> %s</font>' % modstr
            text = '<html>%s<br><font color="silver" size="-2">on</font> %s%s</html>' % (data['title'], maps.getDisplayName(data['mapname']), modhtml)

        self.dialog.newEvent(pixmap, text)

    def dialogClosed(self):
        if self.events:
            self.showEvent()


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

FormClass2, BaseClass2 = util.loadUiType("notification_system/ns_settings.ui")
class NsSettingsDialog(FormClass2, BaseClass2):
    def __init__(self, client, *args, **kwargs):
        BaseClass2.__init__(self, *args, **kwargs)

        self.setupUi(self)
        self.client = client

        # remove help button
        self.setWindowFlags(self.windowFlags() & (~QtCore.Qt.WindowContextHelpButtonHint))

        # TODO: integrate into client.css
        self.setStyleSheet(self.client.styleSheet())


        self.tableView.setModel(NotificationHooks(self))
        # stretch first column
        self.tableView.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)

        self.loadSettings()


    def loadSettings(self):
        util.settings.beginGroup("notification_system")
        self.enabled = util.settings.value('enabled', 'true') == 'true'
        self.popup_lifetime = util.settings.value('popup_lifetime', 5)
        util.settings.endGroup()

        self.nsEnabled.setChecked(self.enabled)
        self.nsPopLifetime.setValue(self.popup_lifetime)


    def saveSettings(self):
        util.settings.beginGroup("notification_system")
        util.settings.setValue('enabled', self.enabled)
        util.settings.setValue('popup_lifetime', self.popup_lifetime)
        util.settings.endGroup()
        util.settings.sync()

        self.client.actionNsEnabled.setChecked(self.enabled)

    @QtCore.pyqtSlot()
    def on_btnSave_clicked(self):
        self.enabled = self.nsEnabled.isChecked()
        self.popup_lifetime = self.nsPopLifetime.value()

        self.saveSettings()
        self.hide()

    @QtCore.pyqtSlot()
    def show(self):
        self.loadSettings()
        super(FormClass2, self).show()

class NotificationHooks(QtCore.QAbstractTableModel):
    def __init__(self, parent, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)

        self.hooks = []
        self.headerdata = ['Type', 'PopUp', 'Sound', 'Settings']

    def rowCount(self, parent):
        return len(self.hooks)

    def columnCount(self, parent):
        return len(self.headerdata)

    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        elif role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        return QtCore.QVariant(self.arraydata[index.row()][index.column()])

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.headerdata[col]
        return None
