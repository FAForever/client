import os

from .production import default_values as production_defaults

# These directories are in Appdata (e.g. C:\ProgramData on some Win7 versions)
if 'ALLUSERSPROFILE' in os.environ:
    APPDATA_DIR = os.path.join(os.environ['ALLUSERSPROFILE'], "FAForever")
else:
    APPDATA_DIR = os.path.join(os.environ['HOME'], "FAForever")

default_values = production_defaults.copy()
default_values['host'] = 'test.faforever.com'
default_values['client/logs/console'] = True
