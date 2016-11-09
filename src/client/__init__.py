# Initialize logging system
import logging

from PyQt4.QtNetwork import QNetworkAccessManager
from enum import IntEnum

from config import Settings
from .player import Player

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

# Initialize all important globals
LOBBY_HOST = Settings.get('lobby/host')
LOBBY_PORT = Settings.get('lobby/port')
LOCAL_REPLAY_PORT = Settings.get('lobby/relay/port')

#TODO: remove me for production
import os
if not 'CI' in os.environ:
    from PyQt4.QtGui import QMessageBox
    QMessageBox.information(None, "BETA client information",
                            "<p>This client always connects to the <b>test server</b>.</p>"
                            "<p>You can't play or chat with non-beta players and all stats will be lost.</p>"
                            "Your account <b>password is 'foo'</b> and your login may be outdated.")


class ClientState(IntEnum):
    '''
    Various states the client can be in.
    '''
    SHUTDOWN = -666  # Going... DOWN!

    DISCONNECTED = -2
    CONNECTING = -1
    NONE = 0
    CONNECTED = 1
    LOGGED_IN = 2

from _clientwindow import ClientWindow

# Do not remove - promoted widget, py2exe does not include it otherwise
from client.theme_menu import ThemeMenu

instance = ClientWindow()

NetworkManager = QNetworkAccessManager(instance)
