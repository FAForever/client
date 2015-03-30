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





from trueSkill.TrueSkill.Layers.TrueSkillFactorGraphLayer import *
from trueSkill.TrueSkill.DrawMargin import *
from trueSkill.TrueSkill.Factors.GaussianGreaterThanFactor import *
from trueSkill.TrueSkill.Factors.GaussianWithinFactor import *

class TeamDifferencesComparisonLayer (TrueSkillFactorGraphLayer) :
    def __init__(self, parentGraph, teamRanks):

        super(TeamDifferencesComparisonLayer, self).__init__(parentGraph)
 
        self._teamRanks = teamRanks
        gameInfo = self.getParentFactorGraph().getGameInfo()
        self._epsilon = DrawMargin.getDrawMarginFromDrawProbability(gameInfo.getDrawProbability(), gameInfo.getBeta())


    def buildLayer(self) :

        inputVarGroups = self.getInputVariablesGroups()
        inputVarGroupsCount = len(inputVarGroups)

        for i in range (inputVarGroupsCount) :
            
            isDraw = False
            
            if self._teamRanks[i] == self._teamRanks[i+1] :
                isDraw = True

            teamDifference = inputVarGroups[i][0]
            
            factor = None

            if isDraw :
                factor = GaussianWithinFactor(self._epsilon, teamDifference)
            else :
                factor = GaussianGreaterThanFactor(self._epsilon, teamDifference);

            self.addLayerFactor(factor)
