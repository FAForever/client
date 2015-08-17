



# Initialize logging system
import logging

from config import Settings

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)


# Initialize all important globals
LOBBY_HOST = Settings.get('HOST', 'LOBBY')
LOBBY_PORT = Settings.get('PORT', 'LOBBY')
LOCAL_REPLAY_PORT = Settings.get('LOCAL_REPLAY_PORT', 'LOBBY')
GAME_PORT_DEFAULT = Settings.get('GAME_PORT_DEFAULT', 'LOBBY')

# Important URLs
MUMBLE_URL = "mumble://{login}@mumble.faforever.com/Games?version=1.2.0" 
FORUMS_URL = "http://forums.faforever.com/forums"
WEBSITE_URL = "http://www.faforever.com"
UNITDB_URL = "http://content.faforever.com/faf/unitsDB/"
WIKI_URL = "http://wiki.faforever.com/"
SUPPORT_URL = "http://forums.faforever.com/forums/viewforum.php?f=3"
TICKET_URL = "https://gitreports.com/issue/FAForever/lobby"
STEAMLINK_URL = "http://app.faforever.com/faf/steam.php"
PASSWORD_RECOVERY_URL = "http://app.faforever.com/faf/forgotPass.php"
NAME_CHANGE_URL = "http://app.faforever.com/faf/userName.php"


class ClientState:
    '''
    Various states the client can be in.
    '''
    SHUTDOWN  = -666  #Going... DOWN!
    DROPPED   = -2 # Connection lost
    REJECTED  = -1
    NONE      = 0
    ACCEPTED  = 1
    CREATED   = 2
    OUTDATED  = 9000
    UPTODATE  = 9001 #It's over nine thousaaand!



from _clientwindow import ClientWindow as Client

instance = Client()
