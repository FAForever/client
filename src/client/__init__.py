#-------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------





# Initialize logging system
import logging
import util
logger = logging.getLogger("faf.client")
#logger.setLevel(logging.DEBUG)

VERSION        = 0
VERSION_STRING = "development"

#Load build number from version file.
if not util.developer():        
    VERSION_STRING = open("version").read()
    VERSION = int(VERSION_STRING.rsplit('.', 1)[1])


# Initialize all important globals
LOBBY_HOST = 'faforever.com'
#LOBBY_HOST = 'localhost'
LOBBY_PORT = 8001
LOCAL_REPLAY_PORT = 15000
GAME_PORT_DEFAULT = 6112

# Important URLs
TEAMSPEAK_URL = "ts3server://faforever.com?port=9987&nickname={login}" #additional teamspeak parameters: &password=serverPassword&channel=MyDefaultChannel &channelpassword=defaultChannelPassword&token=TokenKey&addbookmark=1
FORUMS_URL = "http://faforever.com/forums"
WEBSITE_URL = "http://www.faforever.com"
UNITDB_URL = "http://www.faforever.com/faf/unitsDB/"
WIKI_URL = "http://www.faforever.com/mediawiki/index.php/Main_Page"
SUPPORT_URL = "http://www.faforever.com/forums/viewforum.php?f=3"
TICKET_URL = "http://bitbucket.org/thepilot/falobby/issues"


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
