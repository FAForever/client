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
from PyQt4 import QtGui
logger = logging.getLogger("faf.galacticWar")
logger.setLevel(logging.DEBUG)

LOBBY_HOST = 'direct.faforever.com'
LOBBY_PORT = 10001

TEXTURE_SERVER = "http://direct.faforever.com/faf/images/"

RANKS = {0:["Private", "Corporal", "Sergeant", "Captain", "Major", "Colonel", "General", "Supreme Commander"],
         1:["Paladin", "Legate", "Priest", "Centurion", "Crusader", "Evaluator", "Avatar-of-War", "Champion"],
         2:["Drone", "Node", "Ensign", "Agent", "Inspector", "Starshina", "Commandarm" ,"Elite Commander"],
         3:["Su", "Sou", "Soth", "Ithem", "YthiIs", "Ythilsthe", "YthiThuum", "Suythel Cosethuum"]
         }

FACTIONS = {0:"UEF", 1:"Aeon",2:"Cybran",3:"Seraphim"}
COLOR_FACTIONS = {0:QtGui.QColor(0,0,255), 1:QtGui.QColor(0,255,0),2:QtGui.QColor(255,0,0),3:QtGui.QColor(255,255,0)}

from _gwlobby import LobbyWidget as Lobby



    