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





from Rating import *
from Player import *
from RatingContainer import *

class faPlayer(RatingContainer) :
    def __init__(self, player = None, rating = None):
    
        super(faPlayer, self).__init__()

        if  player :

            self.addPlayer(player, rating)

    def addPlayer(self, player, rating) :

        self.setRating(player, rating)
        return self

    def getPlayer(self) :
        return self.getAllPlayers()[0]
    
    def getRating(self) :
        return self.getAllRatings()[0]

    def setNewRating(self, rating) :

        return self._playerToRating.setValue(self.getAllPlayers()[0], rating)
