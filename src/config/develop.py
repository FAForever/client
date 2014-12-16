__author__ = 'Sheeo'

from os import environ
from os.path import join
from platform import system

from production import defaults as production_defaults

# These directories are in Appdata (e.g. C:\ProgramData on some Win7 versions)
if system() != "Windows":
    #dotFolder for Linux
    APPDATA_DIR = os.path.join(os.environ['HOME'], ".FAForever")
elif 'ALLUSERSPROFILE' in os.environ:
    APPDATA_DIR = os.path.join(os.environ['ALLUSERSPROFILE'], "FAForever")
else: 
    APPDATA_DIR = os.path.join(os.environ['HOME'], "FAForever")

defaults = production_defaults.copy()

defaults['LOG']['LEVEL'] = logging.INFO

defaults['LOBBY']['HOST'] = 'lobby.dev.faforever.com'
defaults['PROXY']['HOST'] = 'proxy.dev.faforever.com'
defaults['ONLINE_REPLAY_SERVER']['HOST'] = 'lobby.dev.faforever.com'
defaults['RELAY_SERVER']['HOST'] = 'lobby.dev.faforever.com'
