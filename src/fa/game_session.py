from functools import partial

from PyQt4.QtCore import QObject
from PyQt4.QtNetwork import QTcpServer, QHostAddress
from enum import IntEnum

from connectivity import QTurnClient
from connectivity.turn import TURNState
from fa.game_connection import GPGNetConnection
from fa.game_process import GameProcess, instance as game_process_instance


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


class GameSession(QObject):
    def __init__(self, client):
        QObject.__init__(self)
        self._state = GameSessionState.OFF

        # Subscribe to messages targeted at 'game' from the server
        client.subscribe_to('game', self)
        # Keep a parent pointer so we can use it to send
        # relay messages about the game state
        self._client = client

        self.game_port = client.gamePort
        self.player = client.me

        # Use the normal lobby by default
        self.init_mode = 1

        # 'GPGNet' TCP listener
        self._game_listener = QTcpServer(self)
        self._game_listener.newConnection.connect(self._new_game_connection)

        # STUN/TURN client
        self._turn_client = QTurnClient()

        # We only allow one game connection at a time
        self._game_connection = None

        self._process = game_process_instance  # type: GameProcess

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, val):
        self._state = val
        self.send('GameSessionState', val.value)

    def perform_connectivity_test(self):
        """
        Ask the server to perform a connectivity test
        :return:
        """
        if not self.state == GameSessionState.LISTENING:
            self.listen()

        def handle_state_changed(state):
            if state == TURNState.BOUND:
                self.send('ConnectivityTest',
                          [self._turn_client.mapped_address,
                           self._turn_client.relay_address])
        self._turn_client.state_changed.connect(handle_state_changed)

    def listen(self):
        """
        Start listening for remote commands

        Call this in good time before hosting a game,
        e.g. when the host game dialog is being shown.
        """
        assert self.state == GameSessionState.OFF
        self._game_listener.listen(QHostAddress.LocalHost)
        self._turn_client.run()
        self.state = GameSessionState.LISTENING

    def handle_launch(self):
        assert self.state == GameSession.LISTENING
        self.state = GameSessionState.LAUNCHED
        self._process.run('')

    def send(self, command_id, args):
        self._client.send({
            'command': command_id,
            'target': 'game',
            'args': args or []
        })

    def _new_game_connection(self):
        assert not self._game_connection
        self._game_connection = GPGNetConnection(self._game_listener.nextPendingConnection())
        self._game_connection.messageReceived.connect(self._on_game_message)
        self.state = GameSessionState.RUNNING

    def _on_game_message(self, command, args):
        if command == "GameState":
            if args[0] == 'Idle':
                # autolobby, port, nickname, uid, hasSupcom
                self._game_connection.send("CreateLobby",
                                            self.init_mode,
                                            self.game_port,
                                            self.me.login,
                                            self.me.id,
                                            1)
                return  # Only initialize the game lobby instance
            elif args[0] == 'Lobby':
                # TODO: Eagerly initialize the game by hosting/joining early
                pass
        self.send(command, args)
