from decorators import with_logger
from PyQt4.QtCore import QProcess
from PyQt4.QtNetwork import QTcpServer, QHostAddress
import os
import sys
from config import Settings
import client

if sys.platform != 'win32':
    from distutils.spawn import find_executable

@with_logger
class IceAdapterProcess(object):
    def __init__(self, player_id, player_login):

        # determine free listen port for the RPC server inside the ice adapter process
        s = QTcpServer()
        s.listen(QHostAddress.LocalHost, 0)
        self._rpc_server_port = s.serverPort()
        s.close()

        log_file = os.path.join(Settings.get('client/logs/path'), 'ice-adapter.log')

        node_executable = "node"

        if sys.platform == 'win32':
            node_executable = os.path.join(os.getcwd(), "faf-ice-adapter", "node.exe")
            adapter_app = os.path.join(os.getcwd(), "faf-ice-adapter", "faf-ice-adapter.js")
            if not os.path.isfile(adapter_app): #running from source with ice-adapter checked out in client root dir
                adapter_app = os.path.join(os.getcwd(), "ice-adapter", "src", "index.js")
        else:
            adapter_app = find_executable('faf-ice-adapter')
        if not os.path.isfile(adapter_app):
            self._logger.error("error finding ice-adapter javascript main file")
            return

        self.ice_adapter_process = QProcess()
        self.ice_adapter_process.start(node_executable,
                                       [adapter_app,
                                        "--id", str(player_id),
                                        "--login", player_login,
                                        "--rpc-port", str(self._rpc_server_port),
                                        "--gpgnet-port", "0",
                                        "--log-file", log_file])


        # wait for the first message which usually means the ICE adapter is listening for JSONRPC connections
        if not self.ice_adapter_process.waitForReadyRead(5000):
            self._logger.error("error starting the ice adapter process")

        self.ice_adapter_process.readyReadStandardOutput.connect(self.on_log_ready)
        self.ice_adapter_process.readyReadStandardError.connect(self.on_error_ready)

    def on_log_ready(self):
        for line in str(self.ice_adapter_process.readAllStandardOutput()).splitlines():
            self._logger.info("ICE: " + line)

    def on_error_ready(self):
        for line in str(self.ice_adapter_process.readAllStandardError()).splitlines():
            self._logger.error("ICE: " + line)

    def rpc_port(self):
        return self._rpc_server_port

    def close(self):
        if self.ice_adapter_process.state() == QProcess.Running:
            self._logger.info("Waiting for ice adapter process shutdown")
            if not self.ice_adapter_process.waitForFinished(300):
                if self.ice_adapter_process.state() == QProcess.Running:
                    self._logger.error("Terminating ice adapter process")
                    self.ice_adapter_process.terminate()
                    if not self.ice_adapter_process.waitForFinished(300):
                        self._logger.error("Killing ice adapter process")
                        self.ice_adapter_process.kill()
