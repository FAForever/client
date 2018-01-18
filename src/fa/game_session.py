from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtNetwork import QTcpServer, QHostAddress
from enum import IntEnum

from connectivity.turn import TURNState
from decorators import with_logger
from fa.game_connection import GPGNetConnection
from fa.game_process import instance

from fa.game_process import GameProcess, instance as game_process_instance
import util
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
    gameFullSignal = pyqtSignal()

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
        self.game_has_started = False

        # Subscribe to messages targeted at 'game' from the server
        client.lobby_dispatch.subscribe_to('game', self.handle_message)

        # Connectivity helper
        self.connectivity = connectivity
        self.connectivity.ready.connect(self.ready.emit)
        self.connectivity.peer_bound.connect(self._peer_bound)

        # Keep a parent pointer so we can use it to send
        # relay messages about the game state
        self._client = client  # type: Client
        self.me = client.me

        self.game_port = client.gamePort

        # Use the normal lobby by default
        self.init_mode = 0
        self._joins, self._connects = [], []

        # 'GPGNet' TCP listener
        self._game_listener = QTcpServer(self)
        self._game_listener.newConnection.connect(self._new_game_connection)
        self._game_listener.listen(QHostAddress.LocalHost)

        # We only allow one game connection at a time
        self._game_connection = None

        self._process = instance  # type:'GameProcess'
        self._process.started.connect(self._launched)
        self._process.finished.connect(self._exited)

    @property
    def relay_port(self):
        return self._game_listener.serverPort()

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, val):
        self._state = val

    def listen(self):
        """
        Start listening for remote commands

        Call this in good time before hosting a game,
        e.g. when the host game dialog is being shown.
        """
        assert self.state == GameSessionState.OFF
        self.state = GameSessionState.LISTENING
        if self.connectivity.is_ready:
            self.ready.emit()
        else:
            self.connectivity.prepare()

    def _needs_game_connection(fn):
        def wrap(self, *args, **kwargs):
            if self._game_connection is None:
                self._logger.warning("{}.{}: tried to run without a game connection".format(
                    self.__class__.__name__, fn.__name__))
            else:
                return fn(self, *args, **kwargs)
        return wrap

    @_needs_game_connection
    def handle_message(self, message):
        command, args = message.get('command'), message.get('args', [])
        if command == 'SendNatPacket':
            addr_and_port, message = args
            host, port = addr_and_port.split(':')
            self.connectivity.send(message, (host, port))
        elif command == 'CreatePermission':
            addr_and_port = args[0]
            host, port = addr_and_port.split(':')
            self.connectivity.permit((host, port))
        elif command == 'JoinGame':
            addr, login, peer_id = args
            self._joins.append(peer_id)
            self.connectivity.bind(addr, login, peer_id)
        elif command == 'ConnectToPeer':
            addr, login, peer_id = args
            self._connects.append(peer_id)
            self.connectivity.bind(addr, login, peer_id)
        else:
            self._game_connection.send(command, *args)

    def send(self, command_id, args):
        self._logger.info("Outgoing relay message {} {}".format(command_id, args))
        self._client.lobby_connection.send({
            'command': command_id,
            'target': 'game',
            'args': args or []
        })

    @_needs_game_connection
    def _peer_bound(self, login, peer_id, port):
        self._logger.info("Bound peer {}/{} to {}".format(login, peer_id, port))
        if peer_id in self._connects:
            self._game_connection.send('ConnectToPeer', '127.0.0.1:{}'.format(port), login, peer_id)
            self._connects.remove(peer_id)
        elif peer_id in self._joins:
            self._game_connection.send('JoinGame', '127.0.0.1:{}'.format(port), login, peer_id)
            self._joins.remove(peer_id)

    def _new_game_connection(self):
        self._logger.info("Game connected through GPGNet")
        assert not self._game_connection
        self._game_connection = GPGNetConnection(self._game_listener.nextPendingConnection())
        self._game_connection.messageReceived.connect(self._on_game_message)
        self.state = GameSessionState.RUNNING

    @_needs_game_connection
    def _on_game_message(self, command, args):
        self._logger.info("Incoming GPGNet: {} {}".format(command, args))
        if command == "GameState":
            if args[0] == 'Idle':
                # autolobby, port, nickname, uid, hasSupcom
                self._game_connection.send("CreateLobby",
                                           self.init_mode,
                                           self.game_port + 1,
                                           self.me.player.login,
                                           self.me.player.id,
                                           1)
            elif args[0] == 'Lobby':
                # TODO: Eagerly initialize the game by hosting/joining early
                pass
            elif args[0] == 'Launching':
                self.game_has_started = True
        elif command == 'Rehost':
            self._rehost = True
        elif command == 'GameFull':
            self.gameFullSignal.emit()
        self.send(command, args)

    def _turn_state_changed(self, val):
        if val == TURNState.BOUND:
            self.ready.emit()

    def _launched(self):
        self._logger.info("Game has started")
        self._add_to_full_gamelog()

    def _limit_replayid_gamelogs(self):
        files = os.listdir(util.LOG_DIR)
        files = map(lambda f: os.path.join(util.LOG_DIR, f), files)
        files = sorted(files, key=os.path.getmtime)
        files = list(map(os.path.basename, files))
        replay_files = [e for e in files if "Replayid" in e]
        while len(replay_files) >= util.MAX_NUMBER_REPLAYID_LOG_FILE:
            os.remove(os.path.join(util.LOG_DIR, replay_files[0]))
            replay_files.pop(0)

    def _add_to_full_gamelog(self):
        if os.path.isfile(util.LOG_FILE_GAME):
            with open(util.LOG_FILE_GAME, 'r') as src, open(os.path.join(util.LOG_DIR, 'game.log'), 'a+') as dst: dst.write(src.read())

    def _clear_initial_gamelog(self):
        with open(util.LOG_FILE_GAME, 'w') as src : pass

    def _write_new_replayid_gamelogs(self, replay_ID):
        if self.game_has_started:
            if os.path.isfile(util.LOG_FILE_GAME):
                end_logname = "{}{}".format(str(replay_ID), '.log')
                with open(util.LOG_FILE_GAME, 'r') as src, open("{}{}".format(os.path.join(util.LOG_DIR, 'Replayid'), end_logname), 'w+') as dst: dst.write(src.read())
            else:
                self._logger.error('No game log found to create the replayid game log file')

    def _exited(self, status):
        self._game_connection = None
        self.state = GameSessionState.OFF
        self._logger.info("Game has exited with status code: {}".format(status))
        self.send('GameState', ['Ended'])

        self._limit_replayid_gamelogs()
        self._write_new_replayid_gamelogs(self.game_uid)
        self.game_has_started = False
        self._add_to_full_gamelog()
        self._clear_initial_gamelog()

        if self._rehost:
            self._client.host_game(title=self.game_name,
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
