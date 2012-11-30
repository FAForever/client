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





from Guard import *


#/**
# * Represents a player who has a Rating.


DEFAULT_PARTIAL_PLAY_PERCENTAGE = 1.0  #// = 100% play time
DEFAULT_PARTIAL_UPDATE_PERCENTAGE = 1.0 # // = receive 100% update
# */
class Player(object):
    def __init__(self, 
                 id, 
                 partialPlayPercentage=DEFAULT_PARTIAL_PLAY_PERCENTAGE, 
                 partialUpdatePercentage=DEFAULT_PARTIAL_UPDATE_PERCENTAGE) :


        # If they don't want to give a player an id, that's ok...
        Guard.argumentInRangeInclusive(partialPlayPercentage, 0.0, 1.0, "partialPlayPercentage")
        Guard.argumentInRangeInclusive(partialUpdatePercentage, 0, 1.0, "partialUpdatePercentage")
        self._Id = id
        self._PartialPlayPercentage = partialPlayPercentage
        self._PartialUpdatePercentage = partialUpdatePercentage


#    /**
#     * The identifier for the player, such as a name.
#     */
    def getId(self) :

        return self._Id;
    
    
#    /**
#     * Indicates the percent of the time the player should be weighted where 0.0 indicates the player didn't play and 1.0 indicates the player played 100% of the time.
#     */
    def getPartialPlayPercentage(self) :
        return self._PartialPlayPercentage

    
#    /**
#     * Indicated how much of a skill update a player should receive where 0.0 represents no update and 1.0 represents 100% of the update.
#     */
    def  getPartialUpdatePercentage(self) :
        return self._PartialUpdatePercentage

    
    def __str__(self) :
        if (self._Id != None) :
            return str(self._Id)

