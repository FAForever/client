from decorators import with_logger
from connectivity.JsonRpcTcpClient import JsonRpcTcpClient
import util
from PyQt4.QtGui import QTableWidgetItem, QMenu

@with_logger
class ConnectivityDialog(object):
    def __init__(self, ice_adapter_client):
        self.client = ice_adapter_client
        self.client.statusChanged.connect(self.updateStatus)

        self.dialog = util.loadUi('connectivity/connectivity.ui')
        self.dialog.finished.connect(self.close)

        self.dialog.table_relays.customContextMenuRequested.connect(self.onContextMenu)

    def onContextMenu(self, point):
        item = self.dialog.table_relays.itemAt(point)
        if item:
            remoteId = int(self.dialog.table_relays.item(item.row(), 0).text())
            remoteLogin = self.dialog.table_relays.item(item.row(), 1).text()
            menu = QMenu(self.dialog)
            reconnectAction = menu.addAction("Reconnect")
            action = menu.exec_(self.dialog.table_relays.mapToGlobal(point))
            if action == reconnectAction:
                self._logger.info("reconnecting to {}({})".format(remoteLogin, remoteId))
                self._logger.info(self.client.call("reconnectToPeer", [remoteId]))
    def show(self):
        self.dialog.show()
        self.client.call("status", callback_result=self.updateStatus)
    def close(self):
        self.dialog.close()
    def updateStatus(self, status):
        self.dialog.label_version.setText(str(status["version"]))
        self.dialog.label_rpc_port.setText(str(status["options"]["rpc_port"]))
        self.dialog.label_log_file.setText(str(status["options"]["log_file"]))
        self.dialog.label_connected.setText(str(status["gpgnet"]["connected"]))
        self.dialog.label_gamestate.setText(str(status["gpgnet"]["game_state"]))

        self.dialog.label_mode.setText(str(status["gpgnet"]["task_string"]))

        self.dialog.table_relays.setRowCount(len(status["relays"]))
        for row, relay in enumerate(status["relays"]):
            self.dialog.table_relays.setItem(row, 0, QTableWidgetItem(str(relay["remote_player_id"])))
            self.dialog.table_relays.setItem(row, 1, QTableWidgetItem(relay["remote_player_login"]))
            self.dialog.table_relays.setItem(row, 2, QTableWidgetItem(relay["ice_agent"]["state"]))
            self.dialog.table_relays.setItem(row, 3, QTableWidgetItem(str(relay["ice_agent"]["datachannel_open"])))
            self.dialog.table_relays.setItem(row, 4, QTableWidgetItem(str(relay["ice_agent"]["loc_cand_addr"])))
            self.dialog.table_relays.setItem(row, 5, QTableWidgetItem(str(relay["ice_agent"]["rem_cand_addr"])))
