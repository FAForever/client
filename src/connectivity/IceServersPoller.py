from PyQt4.QtCore import QObject, QTimer
from decorators import with_logger
from datetime import datetime, timedelta

@with_logger
class IceServersPoller(QObject):
    def __init__(self, dispatcher, ice_adapter_client, lobby_connection):
        QObject.__init__(self)
        self._dispatcher = dispatcher
        self._ice_adapter_client = ice_adapter_client
        self._server_connection = lobby_connection
        self._dispatcher["ice_servers"] = self.handle_ice_servers
        self._valid_until = datetime.now()
        self.request_ice_servers()
        self.min_valid_seconds = 10*3600  # credentials need to be valid for 10h, usual ttl for each request is 24h
        self._last_received_ice_servers = None
        self._last_relayed_ice_servers = None

        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self.check_ice_servers)
        self._check_timer.start(5000)

    def check_ice_servers(self):
        seconds_left = (self._valid_until - datetime.now()).seconds
        if seconds_left < self.min_valid_seconds:
            self._logger.debug("ICE servers expired: requesting new list")
            self.request_ice_servers()

        # check if we have a list not sent to the ice-adapter
        if not self._last_relayed_ice_servers and \
           self._last_received_ice_servers and \
           self._ice_adapter_client.connected:
            self._ice_adapter_client.call("setIceServers", [self._last_received_ice_servers])
            self._last_relayed_ice_servers = self._last_received_ice_servers

    def request_ice_servers(self):
        self._server_connection.send({'command': 'ice_servers'})

    def handle_ice_servers(self, message):
        self._valid_until = datetime.now() + timedelta(seconds=int(message['ttl']))
        self._logger.debug("ice_servers valid until {}".format(self._valid_until))
        self._last_received_ice_servers = message['ice_servers']
        if self._ice_adapter_client.connected:
            self._ice_adapter_client.call("setIceServers", [self._last_received_ice_servers])
            self._last_relayed_ice_servers = self._last_received_ice_servers
        else:
            self._logger.warn("ICE servers received, but not connected to ice-adapter")
