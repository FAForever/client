__author__ = 'Sheeo'

import os
from platform import system
import logging

if system() == "Windows":
    ON_WINDOWS = True
else: 
    ON_WINDOWS = False

# These directories are in Appdata (e.g. C:\ProgramData on some Win7 versions)
if not ON_WINDOWS:
    #dotFolder for Linux
    APPDATA_DIR = os.path.join(os.environ['HOME'], ".FAForever")
elif 'ALLUSERSPROFILE' in os.environ:
    APPDATA_DIR = os.path.join(os.environ['ALLUSERSPROFILE'], "FAForever")
else: 
    APPDATA_DIR = os.path.join(os.environ['HOME'], "FAForever")

if not ON_WINDOWS:
    localfolder = os.path.join(os.environ['HOME'], ".PlayOnLinux", "wineprefix", "SupremeCommander", "drive_c", "users", os.environ['USER'], "Local Settings", "Application Data", "Gas Powered Games", "Supreme Commander Forged Alliance")
else:
    localfolder = os.path.join(os.path.expandvars("%LOCALAPPDATA%"), "Gas Powered Games", "Supreme Commander Forged Alliance")
    if not os.path.exists(localfolder):
        localfolder = os.path.join(os.path.expandvars("%USERPROFILE%"), "Local Settings", "Application Data", "Gas Powered Games", "Supreme Commander Forged Alliance")

GAME_PREFS_PATH = os.path.join(localfolder, "Game.prefs")


defaults = {
    'BASE_DIR': APPDATA_DIR,
    'LOG': {
        'DIR': os.path.join(APPDATA_DIR, 'logs'),
        'LEVEL': logging.WARNING,
        'MAX_SIZE': 256*1024
    },
    'FA': {
        "BIN": os.path.join(APPDATA_DIR, "bin"),
        "ENGINE_PATH": os.path.join(os.path.join(APPDATA_DIR, "repo"), "binary-patch"),
        "MODS_PATH": os.path.join(os.path.join(APPDATA_DIR, "repo"), "mods"),
        "MAPS_PATH": os.path.join(os.path.join(APPDATA_DIR, "repo"), "maps"),
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
