
# Initialize logging system
import logging

logger = logging.getLogger(__name__)

GPGNET_HOST = "lobby.faforever.com"
GPGNET_PORT = 8000

DEFAULT_LIVE_REPLAY = True
DEFAULT_RECORD_REPLAY = True
DEFAULT_WRITE_GAME_LOG = False

# We only want one instance of Forged Alliance to run, so we use a singleton here (other modules may wish to connect to its signals so it needs persistence)
from game_process import instance as instance
from play import run
from replay import replay

import check
import maps
import mods
import replayserver
import updater
import upnp
import factions
