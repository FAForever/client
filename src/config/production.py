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
        'DIR': os.path.join(APPDATA_DIR, 'logs'),
        'LEVEL': logging.WARNING,
        'MAX_SIZE': 256*1024
    },
    'FA': {
        "BIN": os.path.join(APPDATA_DIR, "bin")
    },
    'PROXY': {
        'HOST': 'proxy.faforever.com',
        'PORT': 9134
    },
    'LOBBY': {
        'HOST': 'lobby.faforever.com',
        'PORT': 8001,
        'LOCAL_REPLAY_PORT': 15000,
        'GAME_PORT_DEFAULT': 6112
    },
    'MUMBLE_URL': "mumble://{login}@mumble.faforever.com/Games?version:1.2.0",
    'FORUMS_URL': "http://forums.faforever.com/forums",
    'WEBSITE_URL': "http://www.faforever.com",
    'UNITDB_URL': "http://content.faforever.com/faf/unitsDB/",
    'WIKI_URL': "http://wiki.faforever.com/mediawiki/index.php/Main_Page",
    'SUPPORT_URL': "http://forums.faforever.com/forums/viewforum.php?f:3",
    'TICKET_URL': "http://forums.faforever.com/forums/viewforum.php?f:3",
    'STEAMLINK_URL': "http://app.faforever.com/faf/steam.php",
    'PASSWORD_RECOVERY_URL': "http://www.faforever.com/faf/forgotPass.php",
    'NAME_CHANGE_URL': "http://www.faforever.com/faf/userName.php"
}
