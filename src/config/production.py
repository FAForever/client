__author__ = 'Sheeo'

from os import environ
from os.path import join

import logging

# These directories are in Appdata (e.g. C:\ProgramData on some Win7 versions)
if 'ALLUSERSPROFILE' in environ:
    APPDATA_DIR = join(environ['ALLUSERSPROFILE'], "FAForever")
else:
    APPDATA_DIR = join(environ['HOME'], "FAForever")


defaults = {
    'BASE_DIR': APPDATA_DIR,
    'LOG': {
        'DIR': join(APPDATA_DIR, 'logs'),
        'LEVEL': logging.WARNING,
        'MAX_SIZE': 256*1024
    },
    'FA': {
        "BIN": join(APPDATA_DIR, "bin"),
        "ENGINE_PATH": join(join(APPDATA_DIR, "repo"), "binary-patch"),
        "MODS_PATH": join(join(APPDATA_DIR, "repo"), "mods"),
        "MAPS_PATH": join(join(APPDATA_DIR, "repo"), "maps"),
        "WRITE_GAME_LOG": False
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
    'NAME_CHANGE_URL': "http://www.faforever.com/faf/userName.php",
    'USE_CHAT': True,
    'ONLINE_REPLAY_SERVER': {
        'HOST': 'lobby.faforever.com',
        'PORT': 15000
    },
    'RELAY_SERVER': {
        'HOST': 'lobby.faforever.com',
        'PORT': 8000
    }
}
