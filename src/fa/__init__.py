
# Initialize logging system
import logging

logger = logging.getLogger(__name__)

# We only want one instance of Forged Alliance to run, so we use a singleton here (other modules may wish to connect to its signals so it needs persistence)
from game_process import instance as instance
from .game_session import GameSession
from play import run
from replay import replay

import check
import maps
import mods
import replayserver
import updater
import upnp
import factions
