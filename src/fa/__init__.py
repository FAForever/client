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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

GPGNET_HOST = "lobby.faforever.com"
GPGNET_PORT = 8000

DEFAULT_LIVE_REPLAY = True
DEFAULT_RECORD_REPLAY = True
DEFAULT_WRITE_GAME_LOG = False

# We only want one instance of Forged Alliance to run, so we use a singleton here (other modules may wish to connect to its signals so it needs persistence)
from process import instance as instance
from play import play
from replay import replay

from fa.path import gamepath


import check
import maps
import replayserver
import relayserver
import proxies
import updater
import upnp
import faction
import binary
import featured
