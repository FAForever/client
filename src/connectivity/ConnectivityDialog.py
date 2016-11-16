from decorators import with_logger
from connectivity.JsonRpcTcpClient import JsonRpcTcpClient
import util
from PyQt4.QtGui import QTableWidgetItem, QMenu

@with_logger
class ConnectivityDialog(object):
    def __init__(self, game_session):
        self.client = JsonRpcTcpClient(host="127.0.0.1",
                                       port=game_session.ice_adapter_process.rpc_port(),
                                       requestHandlerInstance=self)

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
        self.updateStatus()
    def close(self):
        self.client.close()
        self.dialog.close()
    def onConnectionStateChanged(self, newState):
        self.updateStatus()
    def onGpgNetMessageReceived(self, header, chunks):
        self.updateStatus()
    def onPeerStateChanged(self, localPlayerId, remotePlayerId, newState):
        self.updateStatus()
    def updateStatus(self):
        status = self.client.call("status")
        if isinstance(status, dict):
            self.dialog.label_connected.setText(str(status["gpgnet"]["connected"]))
            self.dialog.label_gamestate.setText(str(status["gpgnet"]["game_state"]))

            if "host_game" in status["gpgnet"]:
                mode_str = "hosting map {}".format(status["gpgnet"]["host_game"]["map"])
            elif "join_game" in status["gpgnet"]:
                mode_str = "joining game from player {}".format(status["gpgnet"]["join_game"]["remote_player_login"])
            else:
                mode_str = "Idle"
            self.dialog.label_mode.setText(mode_str)

            self.dialog.table_relays.setRowCount(len(status["relays"]))
            for row, relay in enumerate(status["relays"]):
                self.dialog.table_relays.setItem(row, 0, QTableWidgetItem(str(relay["remote_player_id"])))
                self.dialog.table_relays.setItem(row, 1, QTableWidgetItem(relay["remote_player_login"]))
                self.dialog.table_relays.setItem(row, 2, QTableWidgetItem(relay["ice_agent"]["state"]))
                self.dialog.table_relays.setItem(row, 3, QTableWidgetItem(str(relay["ice_agent"]["connected"])))
                self.dialog.table_relays.setItem(row, 4, QTableWidgetItem(str(relay["ice_agent"]["local_candidate"])))
                self.dialog.table_relays.setItem(row, 5, QTableWidgetItem(str(relay["ice_agent"]["remote_candidate"])))
