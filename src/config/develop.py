__author__ = 'Sheeo'

from os import environ
from os.path import join
from platform import system
import logging
from production import defaults as production_defaults

defaults = production_defaults.copy()

defaults['LOG']['LEVEL'] = logging.INFO

defaults['LOBBY']['HOST'] = 'lobby.dev.faforever.com'
defaults['PROXY']['HOST'] = 'proxy.dev.faforever.com'
defaults['ONLINE_REPLAY_SERVER']['HOST'] = 'lobby.dev.faforever.com'
defaults['RELAY_SERVER']['HOST'] = 'lobby.dev.faforever.com'
