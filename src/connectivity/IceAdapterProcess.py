from decorators import with_logger
from PyQt5.QtCore import QProcess
from PyQt5.QtNetwork import QTcpServer, QHostAddress
import os
import sys
from config import Settings
import fafpath

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

        if sys.platform == 'win32':
            exe_path = os.path.join(fafpath.get_libdir(), "faf-ice-adapter.exe")
        else:  # Expect it to be in PATH already
            exe_path = "faf-ice-adapter"

        self.ice_adapter_process = QProcess()
        self.ice_adapter_process.start(exe_path,
                                       ["--id", str(player_id),
                                        "--login", player_login,
                                        "--rpc-port", str(self._rpc_server_port),
                                        "--gpgnet-port", "0",
                                        "--log-level" , "debug",
                                        "--log-directory", Settings.get('client/logs/path', type=str)])

        # wait for the first message which usually means the ICE adapter is listening for JSONRPC connections
        if not self.ice_adapter_process.waitForStarted(5000):
            self._logger.error("error starting the ice adapter process")

        self.ice_adapter_process.readyReadStandardOutput.connect(self.on_log_ready)
        self.ice_adapter_process.readyReadStandardError.connect(self.on_error_ready)

    def on_log_ready(self):
        for line in str(self.ice_adapter_process.readAllStandardOutput()).splitlines():
            if "FAF:" in line:
                self._logger.debug("ICE: " + line)

    def on_error_ready(self):
        for line in str(self.ice_adapter_process.readAllStandardError()).splitlines():
            if "FAF:" in line:
                self._logger.debug("ICE: " + line)

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
