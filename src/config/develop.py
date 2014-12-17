__author__ = 'Sheeo'

from os import environ
from os.path import join
from platform import system
import logging
from production import defaults as production_defaults

# These directories are in Appdata (e.g. C:\ProgramData on some Win7 versions)
if system() != "Windows":
    #dotFolder for Linux
    APPDATA_DIR = join(environ['HOME'], ".FAForever")
elif 'ALLUSERSPROFILE' in environ:
    APPDATA_DIR = join(environ['ALLUSERSPROFILE'], "FAForever")
else: 
    APPDATA_DIR = join(environ['HOME'], "FAForever")

defaults = production_defaults.copy()

defaults['LOG']['LEVEL'] = logging.INFO

defaults['LOBBY']['HOST'] = 'lobby.dev.faforever.com'
defaults['PROXY']['HOST'] = 'proxy.dev.faforever.com'
defaults['ONLINE_REPLAY_SERVER']['HOST'] = 'lobby.dev.faforever.com'
defaults['RELAY_SERVER']['HOST'] = 'lobby.dev.faforever.com'
