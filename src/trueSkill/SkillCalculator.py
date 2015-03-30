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





from GameInfo import *
from PlayersRange import *
from TeamsRange import *


#/** 
# * Base class for all skill calculator implementations.
# */
class SkillCalculator(object):
    def __init__(self, supportedOptions, totalTeamsAllowed, playerPerTeamAllowed) :

        self._supportedOptions = supportedOptions
        self._totalTeamsAllowed = totalTeamsAllowed
        self._playersPerTeamAllowed = playerPerTeamAllowed




    def isSupported(self, option) :
        if option in self._supportedOptions :
            return True
        return False            
        

    def validateTeamCountAndPlayersCountPerTeam(self, teamsOfPlayerToRatings) :

        self.validateTeamCountAndPlayersCountPerTeamWithRanges(teamsOfPlayerToRatings, self._totalTeamsAllowed, self._playersPerTeamAllowed)


    def validateTeamCountAndPlayersCountPerTeamWithRanges(self,
                                                          teams,
                                                          totalTeams,
                                                          playersPerTeam) :
   
        countOfTeams = 0
        
        for currentTeam in teams :
            if not playersPerTeam.isInRange(currentTeam.count()) :

                raise Exception("Player count is not in range")
            
            countOfTeams = countOfTeams + 1

        if not totalTeams.isInRange(countOfTeams) :

            raise Exception("Team range is not in range")


class SkillCalculatorSupportedOptions(object):
    NONE = 0x00
    PARTIAL_PLAY = 0x01
    PARTIAL_UPDATE = 0x02

