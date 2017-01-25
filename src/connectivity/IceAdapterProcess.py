from decorators import with_logger
from PyQt4.QtCore import QProcess, QProcessEnvironment
from PyQt4.QtNetwork import QTcpServer, QHostAddress
import os
from config import Settings
import client

@with_logger
class IceAdapterProcess(object):
    def __init__(self, player_id, player_login):

        #determine free listen port for the RPC server inside the ice adapter process
        s = QTcpServer()
        s.listen(QHostAddress.LocalHost, 0)
        self._rpc_server_port = s.serverPort()
        s.close()

        log_file = os.path.join(Settings.get('client/logs/path'), 'ice-adapter.log')

        path_env = QProcessEnvironment.systemEnvironment()
        path_string = path_env.value("PATH")
        path_string += os.pathsep + os.getcwd()  # the Windows setup places executables in the root/CWD
        path_string += os.pathsep + os.path.join(os.getcwd(), "lib")  # the default download location for travis/Appveyor and running from source
        path_env.insert("PATH", path_string)
        self.ice_adapter_process = QProcess()
        self.ice_adapter_process.setProcessEnvironment(path_env)
        self.ice_adapter_process.start("faf-ice-adapter",
                                       ["--id", str(player_id),
                                        "--login", player_login,
                                        "--rpc-port", str(self._rpc_server_port),
                                        "--ice-port-min", str(client.instance.gamePort),
                                        "--ice-port-max", str(client.instance.gamePortMax),
                                        "--upnp", str(client.instance.useUPnP),
                                        "--gpgnet-port", "0",
                                        "--log-file", log_file])


        #wait for the first message which usually means the ICE adapter is listening for JSONRPC connections
        if not self.ice_adapter_process.waitForReadyRead(1000):
            self._logger.error("error starting the ice adapter process")

        self.ice_adapter_process.readyReadStandardOutput.connect(self.on_log_ready)
        self.ice_adapter_process.readyReadStandardError.connect(self.on_error_ready)

    def on_log_ready(self):
        output = self.ice_adapter_process.readAllStandardOutput()
        self._logger.info("ICE: " + output)

    def on_error_ready(self):
        output = self.ice_adapter_process.readAllStandardError()
        self._logger.error("ICE: " + output)

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
