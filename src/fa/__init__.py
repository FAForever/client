import logging

# We only want one instance of Forged Alliance to run, so we use a singleton
# here (other modules may wish to connect to its signals so it needs
# persistence)
from . import check, factions, maps, mods, replayserver, updater, wizards
from .game_process import instance
from .play import run
from .replay import replay

logger = logging.getLogger(__name__)
