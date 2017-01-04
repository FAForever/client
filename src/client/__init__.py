# Initialize logging system
import logging

from PyQt4.QtNetwork import QNetworkAccessManager
from enum import IntEnum

from config import modules as cfg
from .player import Player

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

# Initialize all important globals
LOBBY_HOST = cfg.lobby.host.get()
LOBBY_PORT = cfg.lobby.port.get()
LOCAL_REPLAY_PORT = cfg.lobby.relay_port.get()


class ClientState(IntEnum):
    '''
    Various states the client can be in.
    '''
    SHUTDOWN = -666  # Going... DOWN!

    # Disconnected state
    # We enter this state if either:
    #  - The user requested it
    #  - We've reconnected too many times
    DISCONNECTED = -4

    RECONNECTING = -3

    # On this state automatically try and reconnect
    DROPPED = -2
    REJECTED = -1
    NONE = 0
    ACCEPTED = 1
    CREATED = 2
    ONLINE = 3
    OUTDATED = 9000
    UPTODATE = 9001  # It's over nine thousaaand!

from _clientwindow import ClientWindow

instance = ClientWindow()

NetworkManager = QNetworkAccessManager(instance)
