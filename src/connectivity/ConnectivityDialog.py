import pprint

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QHeaderView, QInputDialog, QTableWidgetItem

import client as clientwindow
from decorators import with_logger
from util import THEME


@with_logger
class ConnectivityDialog(object):
    COLUMN_ID = 0
    COLUMN_LOGIN = 1
    COLUMN_CONNECTED = 2
    COLUMN_LOCAL = 3
    COLUMN_REMOTE = 4
    COLUMN_ICESTATE = 5
    COLUMN_LOCALOFFER = 6
    COLUMN_TIMETOCONNECTED = 7

    columnCount = 8

    def __init__(self, ice_adapter_client):
        self.client = ice_adapter_client
        self.client.statusChanged.connect(self.onStatus)
        self.client.gpgnetmessageReceived.connect(self.onGpgnetMessage)

        self.dialog = THEME.loadUi('connectivity/connectivity.ui')
        # need to set the parent like this to make sure this dialog closes on
        # closing the client. also needed for consistent theming
        self.dialog.setParent(clientwindow.instance, Qt.Dialog)

        # the table header needs theming,
        # and using "QHeaderView::section { background-color: green; }"
        # in client.css didn't work for horizontal headers
        stylesheet = """
        ::section{
            color:silver;
            background-color: #606060;
            border: none;
            }
        """
        self.dialog.table_relays.horizontalHeader().setStyleSheet(stylesheet)
        self.dialog.table_relays.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch,
        )
        self.dialog.table_relays.horizontalHeader().setFixedHeight(30)
        self.dialog.table_relays.verticalHeader().setSectionResizeMode(
            QHeaderView.Fixed,
        )
        self.dialog.table_relays.verticalHeader().hide()

        self.dialog.finished.connect(self.close)

        self.statusTimer = QTimer()
        self.statusTimer.timeout.connect(self.getStatus)
        self.statusTimer.start(2000)

        self.status = None
        self.dialog.pushButton_debugState.clicked.connect(self.showDebugState)

    def show(self):
        self.dialog.show()
        self.getStatus()

    def close(self):
        self.dialog.close()

    def showDebugState(self):
        if self.status:
            QInputDialog.getMultiLineText(
                self.dialog,
                "ICE adapter state",
                "",
                pprint.pformat(self.status, width=-1),
            )

    def getStatus(self):
        if self.client.isConnected():
            self.client.call("status", callback_result=self.client.onStatus)

    def onGpgnetMessage(self, *unused):
        self.getStatus()

    def onStatus(self, status):
        self.status = status
        self.dialog.label_version.setText(str(status["version"]))
        self.dialog.label_user.setText(
            "{} ({})".format(
                status["options"]["player_login"],
                status["options"]["player_id"],
            ),
        )
        self.dialog.label_rpc_port.setText(str(status["options"]["rpc_port"]))
        self.dialog.label_gpgnet_port.setText(
            str(status["options"]["gpgnet_port"]),
        )
        self.dialog.label_lobby_port.setText(str(status["lobby_port"]))

        if "log_file" in status["options"]:
            self.dialog.label_log_file.setText(
                str(status["options"]["log_file"]),
            )
        else:
            self.dialog.label_log_file.setText("")

        self.dialog.label_connected.setText(str(status["gpgnet"]["connected"]))
        self.dialog.label_gamestate.setText(
            str(status["gpgnet"]["game_state"]),
        )

        self.dialog.label_mode.setText(str(status["gpgnet"]["task_string"]))

        self.dialog.table_relays.setRowCount(len(status["relays"]))
        for row, relay in enumerate(status["relays"]):
            self.dialog.table_relays.setItem(
                row,
                self.COLUMN_ID,
                self.tableItem(str(relay["remote_player_id"])),
            )
            self.dialog.table_relays.setItem(
                row,
                self.COLUMN_LOGIN,
                self.tableItem(relay["remote_player_login"]),
            )
            self.dialog.table_relays.setItem(
                row,
                self.COLUMN_CONNECTED,
                self.tableItem(str(relay["ice"]["connected"])),
            )
            self.dialog.table_relays.setItem(
                row,
                self.COLUMN_LOCAL,
                self.tableItem(relay["ice"]["loc_cand_type"]),
            )
            self.dialog.table_relays.setItem(
                row,
                self.COLUMN_REMOTE,
                self.tableItem(relay["ice"]["rem_cand_type"]),
            )
            self.dialog.table_relays.setItem(
                row,
                self.COLUMN_ICESTATE,
                self.tableItem(relay["ice"]["state"]),
            )
            self.dialog.table_relays.setItem(
                row,
                self.COLUMN_LOCALOFFER,
                self.tableItem(str(relay["ice"]["offerer"])),
            )
            self.dialog.table_relays.setItem(
                row,
                self.COLUMN_TIMETOCONNECTED,
                self.tableItem(str(relay["ice"]["time_to_connected"])),
            )

    def tableItem(self, data):
        item = QTableWidgetItem(str(data))
        item.setTextAlignment(Qt.AlignCenter)
        return item
