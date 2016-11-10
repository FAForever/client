from decorators import with_logger
import util
from PyQt4.QtGui import QTableWidgetItem
from PyQt4.QtCore import Qt
import client as clientwindow

@with_logger
class ConnectivityDialog(object):
    COLUMN_LOGIN = 0
    COLUMN_CONNECTED = 1
    COLUMN_DIRECTCON = 2
    COLUMN_ICESTATE = 3
    COLUMN_ID = 4
    COLUMN_REMOTE_ADDR = 5

    def __init__(self, ice_adapter_client):
        self.client = ice_adapter_client
        self.client.statusChanged.connect(self.updateStatus)
        self.client.gpgnetmessageReceived.connect(self.onGpgnetMessage)

        self.dialog = util.loadUi('connectivity/connectivity.ui')
        # need to set the parent like this to make sure this dialog closes on closing the client.
        # also needed for consistent theming
        self.dialog.setParent(clientwindow.instance, Qt.Dialog)

        # the table header needs theming,
        # and using "QHeaderView::section { background-color: green; }" in client.css didn't work for horizontal headers
        stylesheet = """
        ::section{
            color:silver;
            background-color: #606060;
            border: none;
            }
        """
        self.dialog.table_relays.horizontalHeader().setStyleSheet(stylesheet)

        self.dialog.finished.connect(self.close)

    def show(self):
        self.dialog.show()
        self.client.call("status", callback_result=self.updateStatus)

    def close(self):
        self.dialog.close()

    def onGpgnetMessage(self, *unused):
        self.client.call("status", callback_result=self.updateStatus)

    def updateStatus(self, status):
        self.dialog.label_version.setText(str(status["version"]))
        self.dialog.label_rpc_port.setText(str(status["options"]["rpc_port"]))
        self.dialog.label_log_file.setText(str(status["options"]["log_file"]))
        self.dialog.label_connected.setText(str(status["gpgnet"]["connected"]))
        self.dialog.label_gamestate.setText(str(status["gpgnet"]["game_state"]))

        self.dialog.label_mode.setText(str(status["gpgnet"]["task_string"]))

        self.dialog.table_relays.setRowCount(len(status["relays"]))
        for row, relay in enumerate(status["relays"]):
            self.dialog.table_relays.setItem(row, self.COLUMN_LOGIN, QTableWidgetItem(relay["remote_player_login"]))
            self.dialog.table_relays.setItem(row, self.COLUMN_ID, QTableWidgetItem(str(relay["remote_player_id"])))

            connected_item = QTableWidgetItem("yes") if relay["ice_agent"]["datachannel_open"] else QTableWidgetItem("no")
            self.dialog.table_relays.setItem(row, self.COLUMN_CONNECTED, connected_item)

            self.dialog.table_relays.setItem(row, self.COLUMN_ICESTATE, QTableWidgetItem(relay["ice_agent"]["state"]))

            if relay["ice_agent"]["rem_cand_type"] == 'local':
                direct_connected_item = QTableWidgetItem("direct")
            elif relay["ice_agent"]["rem_cand_type"] == 'stun':
                direct_connected_item = QTableWidgetItem("direct through NAT")
            elif relay["ice_agent"]["rem_cand_type"] == 'prflx':
                direct_connected_item = QTableWidgetItem("direct")
            elif relay["ice_agent"]["rem_cand_type"] == 'relay':
                direct_connected_item = QTableWidgetItem("proxy")
            else:
                direct_connected_item = QTableWidgetItem("unknown ({})".format(relay["ice_agent"]["rem_cand_type"]))
            self.dialog.table_relays.setItem(row, self.COLUMN_DIRECTCON, direct_connected_item)

            self.dialog.table_relays.setItem(row, self.COLUMN_REMOTE_ADDR, QTableWidgetItem(str(relay["ice_agent"]["rem_cand_addr"])))
        for col in range(self.COLUMN_REMOTE_ADDR):
            self.dialog.table_relays.resizeColumnToContents(col)




