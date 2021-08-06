# Initialize logging system
import logging
from enum import IntEnum

from config import Settings

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

# Initialize all important globals
LOBBY_HOST = Settings.get('lobby/host')
LOBBY_PORT = Settings.get('lobby/port', type=int)


class ClientState(IntEnum):
    """
    Various states the client can be in.
    """
    SHUTDOWN = -666  # Going... DOWN!

    DISCONNECTED = -2
    CONNECTING = -1
    NONE = 0
    CONNECTED = 1
    LOGGED_IN = 2


# Do not remove - promoted widget, py2exe does not include it otherwise
from client.theme_menu import ThemeMenu

from ._clientwindow import ClientWindow

instance = ClientWindow()
