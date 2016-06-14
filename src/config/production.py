from os import environ
from os.path import join

import logging

# These directories are in Appdata (e.g. C:\ProgramData on some Win7 versions)
if 'ALLUSERSPROFILE' in environ:
    APPDATA_DIR = join(environ['ALLUSERSPROFILE'], "FAForever")
else:
    APPDATA_DIR = join(environ['HOME'], "FAForever")


defaults = {
    'client/data_path': APPDATA_DIR,
    'client/logs/path': join(APPDATA_DIR, 'logs'),
    'client/logs/level': logging.INFO,
    'client/logs/max_size': 512*1024,
    'client/logs/buffer_size': 8*1024,
    'content/host': 'http://content.{host}',
    'chat/enabled': True,
    'game/bin/path': join(APPDATA_DIR, 'bin'),
    'game/engine/path': join(join(APPDATA_DIR, 'repo'), 'binary-patch'),
    'game/logs/path': join(APPDATA_DIR, 'logs'),
    'game/mods/path': join(join(APPDATA_DIR, 'repo'), 'mods'),
    'game/maps/path': join(join(APPDATA_DIR, 'repo'), 'maps'),
    'host': 'faforever.com',
    'proxy/host': 'proxy.{host}',
    'proxy/port': 9124,
    'lobby/relay/port': 15000,
    'lobby/host': 'lobby.{host}',
    'lobby/port': 8001,
    'mordor/host': 'http://mordor.{host}',
    'turn/host': '{host}',
    'turn/port': 3478,
    'replay_server/host': 'lobby.{host}',
    'replay_server/port': 15000,
    'relay_server/host': 'lobby.{host}',
    'relay_server/port': 8000,
    'MUMBLE_URL': 'mumble://{login}@mumble.faforever.com/Games?version:1.2.0',
    'FORUMS_URL': 'http://forums.faforever.com/forums',
    'WEBSITE_URL': 'http://www.faforever.com',
    'UNITDB_URL': 'http://faforever.com/faf/unitsDB/',
    'GITHUB_URL': 'http://www.github.com/FAForever',
    'WIKI_URL': 'http://wiki.faforever.com/mediawiki/index.php/Main_Page',
    'SUPPORT_URL': 'http://forums.faforever.com/viewforum.php?f=3',
    'TICKET_URL': 'http://forums.faforever.com/viewforum.php?f=3',
    'STEAMLINK_URL': 'http://app.faforever.com/faf/steam.php',
    'PASSWORD_RECOVERY_URL': 'http://app.faforever.com/faf/forgotPass.php',
    'NAME_CHANGE_URL': 'http://app.faforever.com/faf/userName.php',
}
