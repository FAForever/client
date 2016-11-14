from PyQt4.QtCore import QObject, pyqtSignal
from enum import IntEnum

from base import Client
from decorators import with_logger
from fa.game_process import GameProcess, instance as game_process_instance

from connectivity.IceAdapterClient import IceAdapterClient
from connectivity.IceAdapterProcess import IceAdapterProcess
from connectivity.JsonRpcTcpClient import JsonRpcTcpClient

import os

class GameSessionState(IntEnum):
    # Game services are entirely off
    OFF = 0
    # We're listening on the game port
    LISTENING = 1
    # We've verified our connectivity and are idle
    IDLE = 2
    # Game has been launched but we're not connected yet
    LAUNCHED = 3
    # Game is running and we're relaying gpgnet commands
    RUNNING = 4


@with_logger
class GameSession(QObject):
    ready = pyqtSignal()

    def __init__(self, client, connectivity):
        QObject.__init__(self)
        self._state = GameSessionState.OFF
        self._rehost = False
        self.game_uid = None
        self.game_name = None
        self.game_mod = None
        self.game_visibility = None
        self.game_map = None
        self.game_password = None

        # Subscribe to messages targeted at 'game' from the server
        client.subscribe_to('game', self)

        # Keep a parent pointer so we can use it to send
        # relay messages about the game state
        self._client = client  # type: Client
        self.me = client.me

        self.player = client.me

        # Use the normal lobby by default
        self.init_mode = 0
        self._joins, self._connects = [], []

        # We only allow one game connection at a time
        self._game_connection = None

        self._process = game_process_instance  # type: GameProcess
        self._process.started.connect(self._launched)
        self._process.finished.connect(self._exited)

        self.state = GameSessionState.LISTENING

        self._relay_port = 0

        #start the faf-ice-adapter executable
        self.ice_adapter_process = IceAdapterProcess(player_id=self.player.id,
                                                     player_login=self.player.login)
        self.ice_adapter_client = IceAdapterClient(game_session=self,
                                                   port=self.ice_adapter_process.rpc_port())
        self._relay_port = self.ice_adapter_client.call("status")["gpgnet"]["local_port"]
        self._logger.info("ICE adapter started an listening on {} for GPGNet connections".format(self._relay_port))

    def close(self):
        self.ice_adapter_client.call("quit")
        self.ice_adapter_client.close()
        self.ice_adapter_process.close()

    @property
    def relay_port(self):
        return self._relay_port

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, val):
        self._state = val

    def handle_message(self, message):
        command, args = message.get('command'), message.get('args', [])
        if command == 'SendNatPacket':
            #we ignore that for now with the ICE Adapter
            pass
        elif command == 'CreatePermission':
            #we ignore that for now with the ICE Adapter
            pass
        elif command == 'JoinGame':
            login, peer_id = args
            self.ice_adapter_client.call("joinGame", [login, peer_id])
        elif command == 'HostGame':
            self.ice_adapter_client.call("hostGame", [args[0]])
        elif command == 'ConnectToPeer':
            login, peer_id = args
            self.ice_adapter_client.call("connectToPeer", [login, peer_id])
        elif command == 'DisconnectFromPeer':
            self.ice_adapter_client.call("disconnectFromPeer", [args[0]])
        elif command == "SdpRecord":
            peer_id, sdp = args
            self.ice_adapter_client.call("setSdp", [peer_id, sdp])
        else:
            self._logger.warn("sending unhandled GPGNet message {} {}".format(command, args))
            self.ice_adapter_client.call("sendToGpgNet", [command, args])

    def send(self, command_id, args):
        self._logger.info("Outgoing relay message {} {}".format(command_id, args))
        self._client.send({
            'command': command_id,
            'target': 'game',
            'args': args or []
        })

    def _new_game_connection(self):
        self._logger.info("Game connected through GPGNet")
        self.state = GameSessionState.RUNNING
        self.ready.emit()

    def _on_game_message(self, command, args):
        self._logger.info("_on_game_message {}".format(self.game_map))
        self._logger.info("Incoming GPGNet: {} {}".format(command, args))
        if command == 'Rehost':
            self._rehost = True

        self.send(command, args)

    def _launched(self):
        self._logger.info("Game has started")

    def _exited(self, status):
        #self._game_connection = None
        self.state = GameSessionState.OFF
        self._logger.info("Game has exited with status code: {}".format(status))
        self.send('GameState', ['Ended'])

        if self._rehost:
            self.client.host_game(title=self.game_name,
                                  mod=self.game_mod,
                                  visibility=self.game_visibility,
                                  mapname=self.game_map,
                                  password=self.game_password,
                                  is_rehost=True)

        self._rehost = False
        self.game_uid = None
        self.game_name = None
        self.game_mod = None
        self.game_visibility = None
        self.game_map = None
        self.game_password = None
