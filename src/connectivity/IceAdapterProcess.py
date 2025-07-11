import logging
import os
from typing import ClassVar

from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QMessageBox

from src import client
from src.config import Settings
from src.connectivity.IceAdapterManager import IceAdapterPlatformOptions
from src.decorators import with_logger
from src.qt.utils import tcp_server
from src.util import ICE_ADAPTER_DIR


@with_logger
class IceAdapterProcess:
    _logger: ClassVar[logging.Logger]

    def __init__(self, player_id: int, player_login: str, game_id: int, port: int) -> None:
        # determine free listen port for the GPG server inside the ice adapter
        # process
        with tcp_server() as server:
            self._gpgnet_port = server.serverPort()

        self.player_id = player_id
        self.player_login = player_login
        self._port = port

        self.exe_path = ""

        platform = IceAdapterPlatformOptions().name()
        version = Settings.get("iceadapter/version", "")
        if version:
            ext = IceAdapterPlatformOptions().extension()
            self.exe_path = os.path.join(ICE_ADAPTER_DIR, f"faf-pioneer-{version}-{platform}{ext}")
        else:
            for file in sorted(os.listdir(ICE_ADAPTER_DIR), reverse=True):
                if "faf-pioneer" in file and platform in file:
                    self.exe_path = os.path.join(ICE_ADAPTER_DIR, file)

        logs_path = Settings.get("client/logs/path", "", type=str)
        ice_logs_path = os.path.join(logs_path, "iceAdapterLogs")
        self.args = [
            "--user-id", str(player_id),
            "--user-name", player_login,
            "--game-id", str(game_id),
            "--access-token", client.instance.oauth_flow.token(),
            "--api-root", Settings.get("api", "https://api.faforever.com") + "/ice",
            "--gpgnet-port", str(self._gpgnet_port),
            "--gpgnet-client-port", str(self._port),
            "--log-level", "-1",
            "--log-path", ice_logs_path,
        ]

        self.ice_adapter_process = QProcess()
        self.ice_adapter_process.setWorkingDirectory(ICE_ADAPTER_DIR)
        self.ice_adapter_process.readyReadStandardError.connect(self.on_stderr_ready)
        self.ice_adapter_process.errorOccurred.connect(self.on_process_error)
        self.ice_adapter_process.finished.connect(self.on_exit)

    def on_stderr_ready(self) -> None:
        standard_error = self.ice_adapter_process.readAllStandardError()
        self._logger.log(5, "ICEERROR: %s", standard_error.data())

    def on_process_error(self, error: QProcess.ProcessError) -> None:
        self._logger.error("Ice adapter process error: %s", error)

    def on_exit(self, code: int, status: QProcess.ExitStatus) -> None:
        if status == QProcess.ExitStatus.CrashExit:
            self._logger.error("the ICE crashed")
            QMessageBox.critical(
                None, "ICE adapter error",
                "The ICE adapter crashed. Please refaf.",
            )
            return
        if code != 0:
            self._logger.error("The ICE adapter closed with error code %d", code)
            QMessageBox.critical(
                None,
                "ICE adapter error",
                f"The ICE adapter closed with error code {code}. Please refaf.",
            )
            return
        else:
            self._logger.debug("The ICE adapter closed with exit code 0")

    def gpg_port(self) -> int:
        return self._gpgnet_port

    def close(self):
        if self.ice_adapter_process.state() == QProcess.ProcessState.Running:
            self._logger.info("Waiting for ice adapter process shutdown")
            if not self.ice_adapter_process.waitForFinished(1000):
                if self.ice_adapter_process.state() == QProcess.ProcessState.Running:
                    self._logger.error("Terminating ice adapter process")
                    self.ice_adapter_process.terminate()
                    if not self.ice_adapter_process.waitForFinished(1000):
                        self._logger.error("Killing ice adapter process")
                        self.ice_adapter_process.kill()

    def _redact_token(self, args: list[str]) -> list[str]:
        copied = args.copy()
        token_index = copied.index("--access-token") + 1
        copied[token_index] = "[redacted]"
        return copied

    def start(self) -> None:
        redacted = self._redact_token(self.args)
        self._logger.debug("Running ice adapter with '%s'", " ".join((self.exe_path, *redacted)))
        self.ice_adapter_process.start(self.exe_path, self.args)
