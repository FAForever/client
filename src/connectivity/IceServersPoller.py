from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal

from src.api.ApiAccessors import ApiAccessor
from src.connectivity.IceAdapterClient import IceAdapterClient
from src.decorators import with_logger


@with_logger
class IceServersPoller(QObject):
    ice_servers_received = pyqtSignal(list)

    def __init__(self, ice_adapter_client: IceAdapterClient, game_uid: int) -> None:
        QObject.__init__(self)
        self._ice_adapter_client = ice_adapter_client
        self._game_uid = game_uid

        self.ice_servers_received.connect(self.set_ice_servers)

        self._api_accessor = ApiAccessor()
        self.request_ice_servers()

    def request_ice_servers(self) -> None:
        self._api_accessor.get_by_endpoint(
            f"/ice/session/game/{self._game_uid}",
            self.handle_ice_servers,
        )

    def handle_ice_servers(self, message: dict) -> None:
        servers = message["servers"]
        self.ice_servers_received.emit(servers)

    def set_ice_servers(self, servers: list[dict]) -> None:
        if self._ice_adapter_client.connected:
            self._logger.debug("Settings IceServers to: %s", servers)
            self._ice_adapter_client.call("setIceServers", [servers])
        else:
            self._logger.warn("ICE servers received, but not connected to ice-adapter")
