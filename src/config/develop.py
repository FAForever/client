import os
import logging

from production import defaults as production_defaults

# These directories are in Appdata (e.g. C:\ProgramData on some Win7 versions)
if 'ALLUSERSPROFILE' in os.environ:
    APPDATA_DIR = os.path.join(os.environ['ALLUSERSPROFILE'], "FAForever")
else:
    APPDATA_DIR = os.path.join(os.environ['HOME'], "FAForever")

defaults = production_defaults.copy()

defaults['client/log/level'] = logging.INFO
defaults['turn/host'] = 'dev.faforever.com'
defaults['lobby/host'] = 'lobby.dev.faforever.com'
defaults['proxy/host'] = 'proxy.dev.faforever.com'
defaults['replay_server/host'] = 'lobby.dev.faforever.com'
defaults['relay_server/host'] = 'lobby.dev.faforever.com'
defaults['content/host'] = 'http://content.test.faforever.com'
defaults['mordor/host'] = 'http://mordor.test.faforever.com'
