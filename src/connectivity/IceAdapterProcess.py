import os
import sys

from PyQt5.QtCore import QProcess, QProcessEnvironment
from PyQt5.QtNetwork import QHostAddress, QTcpServer
from PyQt5.QtWidgets import QMessageBox

import fafpath
from config import Settings
from decorators import with_logger


@with_logger
class IceAdapterProcess(object):
    def __init__(self, player_id, player_login):

        # determine free listen port for the RPC server inside the ice adapter
        # process
        s = QTcpServer()
        s.listen(QHostAddress.LocalHost, 0)
        self._rpc_server_port = s.serverPort()
        s.close()

        if sys.platform == 'win32':
            exe_path = os.path.join(
                fafpath.get_libdir(), "ice-adapter", "faf-ice-adapter.exe",
            )
        else:  # Expect it to be in PATH already
            exe_path = "faf-ice-adapter"

        show_adapter_window = Settings.get(
            "iceadapter/info_window", default=False, type=bool,
        )
        delay_adapter_ui = 1000 * Settings.get(
            "iceadapter/delay_ui_seconds", default=10, type=int,
        )
        self.ice_adapter_process = QProcess()
        args = [
            "--id", str(player_id),
            "--login", player_login,
            "--rpc-port", str(self._rpc_server_port),
            "--gpgnet-port", "0",
            "--log-level", "debug",
        ]
        if show_adapter_window:
            args.extend(["--info-window", "--delay-ui", str(delay_adapter_ui)])
        if Settings.contains('iceadapter/args'):
            args.extend(
                Settings.get('iceadapter/args', "", type=str).split(" "),
            )

        self._logger.debug(
            "running ice adapter with {} {}".format(exe_path, " ".join(args)),
        )

        # set log directory via ENV
        env = QProcessEnvironment.systemEnvironment()
        env.insert(
            "LOG_DIR",
            os.path.join(
                Settings.get('client/logs/path', type=str), 'iceAdapterLogs',
            ),
        )
        self.ice_adapter_process.setProcessEnvironment(env)

        self.ice_adapter_process.start(exe_path, args)

        # wait for the first message which usually means the ICE adapter is
        # listening for JSONRPC connections
        if not self.ice_adapter_process.waitForStarted(5000):
            self._logger.error("error starting the ice adapter process")
            QMessageBox.critical(
                None,
                "ICE adapter error",
                "The ICE adapter did not start. Please refaf.",
            )

        self.ice_adapter_process.readyReadStandardOutput.connect(
            self.on_log_ready,
        )
        self.ice_adapter_process.readyReadStandardError.connect(
            self.on_error_ready,
        )
        self.ice_adapter_process.finished.connect(self.on_exit)

    def on_log_ready(self):
        standard_output = str(self.ice_adapter_process.readAllStandardOutput())
        for line in standard_output.splitlines():
            self._logger.debug("ICE: " + line)

    def on_error_ready(self):
        standard_error = str(self.ice_adapter_process.readAllStandardError())
        for line in standard_error.splitlines():
            self._logger.debug("ICEERROR: " + line)

    def on_exit(self, code, status):
        if status == QProcess.CrashExit:
            self._logger.error("the ICE crashed")
            QMessageBox.critical(
                None, "ICE adapter error",
                "The ICE adapter crashed. Please refaf.",
            )
            return
        if code != 0:
            self._logger.error("The ICE adapter closed with error code", code)
            QMessageBox.critical(
                None,
                "ICE adapter error",
                (
                    "The ICE adapter closed with error code {}. Please refaf."
                    .format(code)
                ),
            )
            return
        else:
            self._logger.debug("The ICE adapter closed with exit code 0")

    def rpc_port(self):
        return self._rpc_server_port

    def close(self):
        if self.ice_adapter_process.state() == QProcess.Running:
            self._logger.info("Waiting for ice adapter process shutdown")
            if not self.ice_adapter_process.waitForFinished(1000):
                if self.ice_adapter_process.state() == QProcess.Running:
                    self._logger.error("Terminating ice adapter process")
                    self.ice_adapter_process.terminate()
                    if not self.ice_adapter_process.waitForFinished(1000):
                        self._logger.error("Killing ice adapter process")
                        self.ice_adapter_process.kill()
