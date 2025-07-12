import logging
import os
import textwrap
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from PyQt6.QtCore import QProcess
from PyQt6.QtCore import QProcessEnvironment
from PyQt6.QtWidgets import QMessageBox

from src import client
from src import fafpath
from src.config import Settings
from src.connectivity.IceAdapterManager import GoIceAdapterPlatformOptions
from src.connectivity.IceAdapterManager import IceAdapterPlatformOptions
from src.connectivity.IceAdapterManager import JavaIceAdapterPlatformOptions
from src.decorators import with_logger
from src.qt.utils import tcp_server
from src.util import ICE_ADAPTER_DIR


@dataclass(frozen=True)
class IceProcessArguments(ABC):
    player_id: int
    player_login: str
    game_id: int
    port: int
    gpg_port: int

    @abstractmethod
    def exe_path(self) -> str: ...
    @abstractmethod
    def arguments(self) -> list[str]: ...
    @abstractmethod
    def exe_prefix(self) -> str: ...
    @abstractmethod
    def platform_options(self) -> IceAdapterPlatformOptions: ...

    def resolved_filename(self) -> str:
        options = self.platform_options()
        platform = options.name()
        kind = Settings.get("iceadapter/kind", "java")
        version = (
            Settings.get(f"iceadapter/{kind}_version", "")
            or Settings.get(f"iceadapter/{kind}_latest", "")
        )
        if version:
            ext = options.extension()
            return os.path.join(ICE_ADAPTER_DIR, f"{self.exe_prefix()}-{version}-{platform}{ext}")
        else:
            for file in sorted(os.listdir(ICE_ADAPTER_DIR), reverse=True):
                if self.exe_prefix() in file and platform in file:
                    return os.path.join(ICE_ADAPTER_DIR, file)
        return ""


@dataclass(frozen=True)
class JavaProcessArguments(IceProcessArguments):
    def exe_prefix(self) -> str:
        return "faf-ice-adapter"

    def platform_options(self) -> IceAdapterPlatformOptions:
        return JavaIceAdapterPlatformOptions()

    def exe_path(self) -> str:
        return fafpath.get_java_path()

    def arguments(self) -> list[str]:
        show_adapter_window = Settings.get("iceadapter/info_window", default=False, type=bool)
        delay_adapter_ui = 1000 * Settings.get("iceadapter/delay_ui_seconds", default=10, type=int)
        args = [
            "-jar", self.resolved_filename(),
            "--id", str(self.player_id),
            "--login", self.player_login,
            "--game-id", str(self.game_id),
            "--rpc-port", str(self.port),
            "--gpgnet-port", str(self.gpg_port),
        ]
        if show_adapter_window:
            args.extend(["--info-window", "--delay-ui", str(delay_adapter_ui)])
        if Settings.contains("iceadapter/args"):
            args.extend(Settings.get("iceadapter/args", "", type=str).split(" "))
        return args


@dataclass(frozen=True)
class GoProcessArguments(IceProcessArguments):
    log_path: str

    def exe_prefix(self) -> str:
        return "faf-pioneer"

    def platform_options(self) -> IceAdapterPlatformOptions:
        return GoIceAdapterPlatformOptions()

    def exe_path(self) -> str:
        return self.resolved_filename()

    def arguments(self) -> list[str]:
        return [
            "--user-id", str(self.player_id),
            "--user-name", self.player_login,
            "--game-id", str(self.game_id),
            "--access-token", client.instance.oauth_flow.token(),
            "--api-root", Settings.get("api", "https://api.faforever.com") + "/ice",
            "--gpgnet-port", str(self.gpg_port),
            "--gpgnet-client-port", str(self.port),
            "--log-level", "-1",
            "--log-path", self.log_path,
        ]


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

        self.ice_adapter_process = QProcess()
        self.ice_adapter_process.setWorkingDirectory(ICE_ADAPTER_DIR)
        self.ice_adapter_process.readyReadStandardError.connect(self.on_stderr_ready)
        self.ice_adapter_process.errorOccurred.connect(self.on_process_error)
        self.ice_adapter_process.finished.connect(self.on_exit)

        adapter = Settings.get("iceadapter/kind", "java")
        if adapter == "java":
            self.process_args = JavaProcessArguments(
                player_id,
                player_login,
                game_id,
                port,
                self._gpgnet_port,
            )
            env = QProcessEnvironment.systemEnvironment()
            env.insert(
                "LOG_DIR",
                os.path.join(Settings.get("client/logs/path", ""), "iceAdapterLogs"),
            )
            self.ice_adapter_process.setProcessEnvironment(env)
        else:
            logs_path = Settings.get("client/logs/path", "", type=str)
            ice_logs_path = os.path.join(logs_path, "iceAdapterLogs")
            self.process_args = GoProcessArguments(
                player_id,
                player_login,
                game_id,
                port,
                self._gpgnet_port,
                ice_logs_path,
            )

        self.exe_path = self.process_args.exe_path()
        self.args = self.process_args.arguments()

    def on_stderr_ready(self) -> None:
        standard_error = self.ice_adapter_process.readAllStandardError()
        self._logger.log(5, "ICEERROR: %s", standard_error.data())

    def on_process_error(self, error: QProcess.ProcessError) -> None:
        self._logger.error("Ice adapter process error: %s", error)

    def on_exit(self, code: int, status: QProcess.ExitStatus) -> None:
        advice = textwrap.dedent("""
        Please check that you are using the correct ICE adapter (Options -> ICE Adapter...)
        Or refaf
        Or try selecting different ICE Adapter version (Options -> ICE Adapter -> Use specific versions...)
        """)  # noqa: E501
        if status == QProcess.ExitStatus.CrashExit:
            self._logger.error("the ICE crashed")
            QMessageBox.critical(
                None, "ICE adapter error",
                f"The ICE adapter crashed.\n{advice}",
            )
            return
        if code != 0:
            self._logger.error("The ICE adapter closed with error code %d", code)
            QMessageBox.critical(
                None,
                "ICE adapter error",
                f"The ICE adapter closed with error code {code}.\n{advice}",
            )
            return
        else:
            self._logger.debug("The ICE adapter closed with exit code 0")

    def port(self) -> int:
        return self._port

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
        try:
            token_index = copied.index("--access-token") + 1
            copied[token_index] = "[redacted]"
        except ValueError:
            pass
        return copied

    def start(self) -> None:
        redacted = self._redact_token(self.args)
        self._logger.debug("Running ice adapter with '%s'", " ".join((self.exe_path, *redacted)))
        self.ice_adapter_process.start(self.exe_path, self.args)
