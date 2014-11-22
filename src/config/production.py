__author__ = 'Sheeo'

import os
import logging

# These directories are in Appdata (e.g. C:\ProgramData on some Win7 versions)
if 'ALLUSERSPROFILE' in os.environ:
    APPDATA_DIR = os.path.join(os.environ['ALLUSERSPROFILE'], "FAForever")
else:
    APPDATA_DIR = os.path.join(os.environ['HOME'], "FAForever")

defaults = {
    'BASE_DIR': APPDATA_DIR,
    'LOG': {
        'FAF': os.path.join(APPDATA_DIR, "logs/forever.log"),
        'GAME': os.path.join(APPDATA_DIR, "logs/game.log"),
        'REPLAY': os.path.join(APPDATA_DIR, "logs/replay.log"),
        'LEVEL': logging.WARNING
    },
    'FA': {
        "BIN": os.path.join(APPDATA_DIR, "bin")
    },
    'PROXY': {
        'HOST': 'proxy.faforever.com',
        'PORT': 9134
    }
}
