from os import environ
from os.path import join

import logging

# These directories are in Appdata (e.g. C:\ProgramData on some Win7 versions)
if 'ALLUSERSPROFILE' in environ:
    APPDATA_DIR = join(environ['ALLUSERSPROFILE'], "FAForever")
else:
    APPDATA_DIR = join(environ['HOME'], "FAForever")


default_values = {
    'display_name': 'Main Server (recommended)',
    'api': 'https://api.{host}',
    'chat/host': 'irc.{host}',
    'chat/port': 6697,
    'client/data_path': APPDATA_DIR,
    'client/logs/path': join(APPDATA_DIR, 'logs'),
    'client/logs/level': logging.INFO,
    'client/logs/max_size': 512*1024,
    'client/logs/buffer_size': 8*1024,
    'client/logs/console': False,
    'content/host': 'https://content.{host}',
    'chat/enabled': True,
    'game/bin/path': join(APPDATA_DIR, 'bin'),
    'game/engine/path': join(join(APPDATA_DIR, 'repo'), 'binary-patch'),
    'game/logs/path': join(APPDATA_DIR, 'logs'),
    'game/mods/path': join(join(APPDATA_DIR, 'repo'), 'mods'),
    'game/maps/path': join(join(APPDATA_DIR, 'repo'), 'maps'),
    'host': 'faforever.com',
    'proxy/host': 'proxy.{host}',
    'proxy/port': 9124,
    'lobby/host': 'lobby.{host}',
    'lobby/port': 8001,
    'updater/host': 'lobby.{host}',
    'mordor/host': 'http://mordor.{host}',
    'news/host': 'https://direct.{host}',
    'turn/host': '{host}',
    'turn/port': 3478,
    'oauth/client_id': 'faf-python-client',
    'oauth/host': "https://hydra.{host}",
    'oauth/redirect_uri': "http://localhost",
    'oauth/scope': ["openid", "offline", "public_profile", "lobby"],
    'oauth/token': None,
    'replay_vault/host': 'https://replay.{host}',
    'replay_server/host': 'lobby.{host}',
    'replay_server/port': 15000,
    'relay_server/host': 'lobby.{host}',
    'relay_server/port': 8000,
    'FORUMS_URL': 'https://forums.faforever.com/',
    'WEBSITE_URL': 'https://www.{host}',
    # FIXME - temporary address below
    # The base64 settings string disables expensive loading of all previews
    'UNITDB_URL': 'https://unitdb.faforever.com?settings64=eyJwcmV2aWV3Q29ybmVyIjoiTm9uZSJ9',
    'UNITDB_SPOOKY_URL': 'https://spooky.github.io/unitdb/',
    'MAPPOOL_URL': 'https://forum.faforever.com/topic/148/matchmaker-pools-thread',
    'GITHUB_URL': 'https://www.github.com/FAForever',
    'WIKI_URL': 'https://wiki.faforever.com',
    'SUPPORT_URL': 'https://forum.faforever.com/category/9/faf-support-client-and-account-issues',
    'TICKET_URL': 'https://forum.faforever.com/category/9/faf-support-client-and-account-issues',
    'CREATE_ACCOUNT_URL': 'https://faforever.com/account/register',
    'STEAMLINK_URL': 'https://faforever.com/account/link',
    'PASSWORD_RECOVERY_URL': 'https://faforever.com/account/password/reset',
    'NAME_CHANGE_URL': 'https://faforever.com/account/username/change',
}
