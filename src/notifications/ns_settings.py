"""
The UI of the Notification System Settings Frame.
Each module/hook for the notification system must be registered here.
"""
from enum import Enum
from typing import Any

from PyQt6 import QtCore
from PyQt6 import QtWidgets

import src.notifications as ns
from src import util
from src.config import Settings
from src.notifications.hook_game_launched import NsHookGameLaunchedCustom
from src.notifications.hook_game_launched import NsHookGameLaunchedLadder
from src.notifications.hook_gamefull import NsHookGameFull
from src.notifications.hook_newgame import NsHookNewGame
from src.notifications.hook_partyinvite import NsHookPartyInvite
from src.notifications.hook_useronline import NsHookUserOnline
from src.notifications.ns_hook import NsHook


class IngameNotification(Enum):
    ENABLE = 0
    DISABLE = 1
    QUEUE = 2


class NotificationPosition(Enum):
    BOTTOM_RIGHT = 0
    TOP_RIGHT = 1
    BOTTOM_LEFT = 2
    TOP_LEFT = 3

    def getLabel(self):
        if self == NotificationPosition.BOTTOM_RIGHT:
            return "bottom right"
        elif self == NotificationPosition.TOP_RIGHT:
            return "top right"
        elif self == NotificationPosition.BOTTOM_LEFT:
            return "bottom left"
        elif self == NotificationPosition.TOP_LEFT:
            return "top left"


# TODO: how to register hooks?
FormClass2, BaseClass2 = util.THEME.loadUiType(
    "notification_system/ns_settings.ui",
)


class NsSettingsDialog(FormClass2, BaseClass2):
    def __init__(self, client):
        BaseClass2.__init__(self)
        # BaseClass2.__init__(self, client)

        self.setupUi(self)
        self.client = client

        # remove help button
        self.setWindowFlags(
            self.windowFlags() & (~QtCore.Qt.WindowType.WindowContextHelpButtonHint),
        )

        # init hooks
        self.hooks = {}
        self.hooks[ns.Notifications.USER_ONLINE] = NsHookUserOnline()
        self.hooks[ns.Notifications.NEW_GAME] = NsHookNewGame()
        self.hooks[ns.Notifications.GAME_FULL] = NsHookGameFull()
        self.hooks[ns.Notifications.PARTY_INVITE] = NsHookPartyInvite()
        self.hooks[ns.Notifications.CUSTOM_GAME_LAUNCHED] = NsHookGameLaunchedCustom()
        self.hooks[ns.Notifications.LADDER_GAME_LAUNCHED] = NsHookGameLaunchedLadder()
        self.hooks[ns.Notifications.LAUNCHING_LADDER] = NsHook(ns.Notifications.LAUNCHING_LADDER)

        model = NotificationHooks(self, list(self.hooks.values()))
        self.tableView.setModel(model)
        # stretch first column
        self.tableView.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.Stretch,
        )

        for row in range(0, model.rowCount(None)):
            self.tableView.setIndexWidget(
                model.createIndex(row, 4),
                model.getHook(row).settings(),
            )

        self.loadSettings()

    def loadSettings(self):
        self.enabled = Settings.get('notifications/enabled', True, type=bool)
        self.popup_lifetime = Settings.get(
            'notifications/popup_lifetime', 5, type=int,
        )
        self.popup_position = NotificationPosition(
            Settings.get(
                'notifications/popup_position',
                NotificationPosition.BOTTOM_RIGHT.value,
                type=int,
            ),
        )
        self.ingame_notifications = IngameNotification(
            Settings.get(
                'notifications/ingame', IngameNotification.ENABLE, type=int,
            ),
        )

        self.nsEnabled.setChecked(self.enabled)
        self.nsPopLifetime.setValue(self.popup_lifetime)
        self.nsPositionComboBox.setCurrentIndex(self.popup_position.value)
        self.nsIngameComboBox.setCurrentIndex(self.ingame_notifications.value)

    def saveSettings(self):
        Settings.set('notifications/enabled', self.enabled)
        Settings.set('notifications/popup_lifetime', self.popup_lifetime)
        Settings.set('notifications/popup_position', self.popup_position.value)
        Settings.set('notifications/ingame', self.ingame_notifications.value)

        self.client.actionNsEnabled.setChecked(self.enabled)

    @QtCore.pyqtSlot()
    def on_btnSave_clicked(self):
        self.enabled = self.nsEnabled.isChecked()
        self.popup_lifetime = self.nsPopLifetime.value()
        self.popup_position = NotificationPosition(
            self.nsPositionComboBox.currentIndex(),
        )
        self.ingame_notifications = IngameNotification(
            self.nsIngameComboBox.currentIndex(),
        )

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

    def ingame_allowed(self, event_type: str) -> bool:
        if event_type in self.hooks:
            return self.hooks[event_type].ingame_allowed()
        return False

    def getCustomSetting(self, eventType, key):
        if eventType in self.hooks:
            if hasattr(self.hooks[eventType], key):
                return getattr(self.hooks[eventType], key)
        return None


class NotificationHooks(QtCore.QAbstractTableModel):
    """
    Model Class for notification type table.
    Needs an NsHook.
    """

    POPUP = 1
    SOUND = 2
    ALLOW_INGAME = 3
    SETTINGS = 4

    def __init__(self, parent, hooks, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.da = True
        self.hooks = hooks
        self.headerdata = ['Type', 'PopUp', 'Sound', 'Allow ingame', '#']

    def flags(self, index):
        flags = super(QtCore.QAbstractTableModel, self).flags(index)
        if index.column() in (self.POPUP, self.SOUND, self.ALLOW_INGAME):
            return flags | QtCore.Qt.ItemFlag.ItemIsUserCheckable
        if index.column() == self.SETTINGS:
            return flags | QtCore.Qt.ItemFlag.ItemIsEditable
        return flags

    def rowCount(self, parent):
        return len(self.hooks)

    def columnCount(self, parent):
        return len(self.headerdata)

    def getHook(self, row):
        return self.hooks[row]

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole.EditRole):
        if not index.isValid():
            return None

        # if role == QtCore.Qt.ItemDataRole.TextAlignmentRole and index.column() != 0:
        #    return QtCore.Qt.AlignmentFlag.AlignHCenter

        if role == QtCore.Qt.ItemDataRole.CheckStateRole:
            if index.column() == self.POPUP:
                return self.returnChecked(
                    self.hooks[index.row()].popupEnabled(),
                )
            if index.column() == self.SOUND:
                return self.returnChecked(
                    self.hooks[index.row()].soundEnabled(),
                )
            if index.column() == self.ALLOW_INGAME:
                return self.returnChecked(
                    self.hooks[index.row()].ingame_allowed(),
                )
            return None

        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None

        if index.column() == 0:
            return self.hooks[index.row()].getEventDisplayName()
        return ''

    def returnChecked(self, state):
        return QtCore.Qt.CheckState.Checked if state else QtCore.Qt.CheckState.Unchecked

    def setData(
            self,
            index: QtCore.QModelIndex,
            value: Any,
            role: QtCore.Qt.ItemDataRole = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        if index.column() == self.POPUP:
            self.hooks[index.row()].switchPopup()
            self.dataChanged.emit(index, index)
            return True
        if index.column() == self.SOUND:
            self.hooks[index.row()].switchSound()
            self.dataChanged.emit(index, index)
            return True
        if index.column() == self.ALLOW_INGAME:
            self.hooks[index.row()].switch_ingame()
            self.dataChanged.emit(index, index)
            return True
        return False

    def headerData(self, col, orientation, role):
        if (
            orientation == QtCore.Qt.Orientation.Horizontal
            and role == QtCore.Qt.ItemDataRole.DisplayRole
        ):
            return self.headerdata[col]
        return None
