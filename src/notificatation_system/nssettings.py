from PyQt4 import QtCore, QtGui
import util
import notificatation_system as ns


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


        # init hooks
        self.hooks = {}
        self.hooks[ns.NotificationSystem.USER_ONLINE] = Hook(ns.NotificationSystem.USER_ONLINE)
        self.hooks[ns.NotificationSystem.NEW_GAME] = Hook(ns.NotificationSystem.NEW_GAME)

        self.tableView.setModel(NotificationHooks(self, self.hooks.values()))
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

    def popupEnabled(self, eventType):
        if eventType in self.hooks:
            return self.hooks[eventType].popupEnabled()
        return False

    def soundEnabled(self, eventType):
        if eventType in self.hooks:
            return self.hooks[eventType].soundEnabled()
        return False

class Hook():
    def __init__(self, eventType):
        self.eventType = eventType
        self.loadSettings()

    def loadSettings(self):
        util.settings.beginGroup("notification_system")
        util.settings.beginGroup(self.eventType)
        self.popup = util.settings.value('popup', 'true') == 'true'
        self.sound = util.settings.value('sound', 'true') == 'true'
        util.settings.endGroup()
        util.settings.endGroup()

    def saveSettings(self):
        util.settings.beginGroup("notification_system")
        util.settings.beginGroup(self.eventType)
        util.settings.setValue('popup', self.popup)
        util.settings.setValue('sound', self.sound)
        util.settings.endGroup()
        util.settings.endGroup()
        util.settings.sync()

    def getEventDisplayName(self):
        return self.eventType

    def popupEnabled(self):
        return self.popup

    def switchPopup(self):
        self.popup = not self.popup
        self.saveSettings()

    def soundEnabled(self):
        return self.sound

    def switchSound(self):
        self.sound = not self.sound
        self.saveSettings()

class NotificationHooks(QtCore.QAbstractTableModel):
    POPUP = 1
    SOUND = 2

    def __init__(self, parent, hooks, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.da = True
        self.hooks = hooks
        self.headerdata = ['Type', 'PopUp', 'Sound', 'Settings']

    def flags(self, index):
        flags = super(QtCore.QAbstractTableModel, self).flags(index)
        if index.column() == self.POPUP or index.column() == self.SOUND:
            return  flags | QtCore.Qt.ItemIsUserCheckable
        return flags

    def rowCount(self, parent):
        return len(self.hooks)

    def columnCount(self, parent):
        return len(self.headerdata)

    def data(self, index, role = QtCore.Qt.EditRole):
        if not index.isValid():
            return None

        #if role == QtCore.Qt.TextAlignmentRole and index.column() != 0:
        #    return QtCore.Qt.AlignHCenter

        if role == QtCore.Qt.CheckStateRole:
            if index.column() == self.POPUP:
                return self.returnChecked(self.hooks[index.row()].popupEnabled())
            if index.column() == self.SOUND:
                return self.returnChecked(self.hooks[index.row()].soundEnabled())
            return None

        if role != QtCore.Qt.DisplayRole:
            return None

        if index.column() == 0:
            return self.hooks[index.row()].getEventDisplayName()
        return ''

    def returnChecked(self, state):
        return QtCore.Qt.Checked if state else QtCore.Qt.Unchecked

    def setData(self, index, value, role = QtCore.Qt.EditRole):
        if index.column() == self.POPUP:
            self.hooks[index.row()].switchPopup()
            self.dataChanged.emit(index, index)
            return True
        if index.column() == self.SOUND:
            self.hooks[index.row()].switchSound()
            self.dataChanged.emit(index, index)
            return True
        return False

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.headerdata[col]
        return None