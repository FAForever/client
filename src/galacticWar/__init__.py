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
logger = logging.getLogger("faf.galacticWar")
logger.setLevel(logging.DEBUG)

LOBBY_HOST = 'direct.faforever.com'
LOBBY_PORT = 10001

UEF_RANKS = ["Private", "Corporal", "Sergeant", "Captain", "Major", "Lieutenant", "General", "Supreme Commander"]
CYBRAN_RANKS = ["Ensign", "Drone", "Agent", "Inspector", "Starshina", "Commandarm" ,"Elite Commander", "Supreme Commander"]
AEON_RANKS = ["Crusader", "Legate", "Avatar-of-War", "Priest", "Centurion", "Executor", "Evaluator", "Supreme Commander"]
SERAPHIM_RANKS = ["SouIstle", "Sou", "SouThuum", "YthiIstle", "Ythi", "YthiThuum", "Azeel", "Supreme Commander"]

from _gwlobby import LobbyWidget as Lobby



    