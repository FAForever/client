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
from trueSkill.TrueSkill.Factors.GaussianWeightedSumFactor import *

class TeamPerformancesToTeamPerformanceDifferencesLayer(TrueSkillFactorGraphLayer) :
    
    def __init__(self, parentGraph) :
        super(TeamPerformancesToTeamPerformanceDifferencesLayer, self).__init__(parentGraph)
    


    def buildLayer(self) :
        inputVariablesGroups = self.getInputVariablesGroups()
        inputVariablesGroupsCount = len(inputVariablesGroups)
        outputVariablesGroup = self.getOutputVariablesGroups()

        for i in range(inputVariablesGroupsCount - 1) :


            strongerTeam = inputVariablesGroups[i][0]
            weakerTeam = inputVariablesGroups[i + 1][0]

            currentDifference = self.createOutputVariable()
            newDifferencesFactor = self.createTeamPerformanceToDifferenceFactor(strongerTeam, weakerTeam, currentDifference)
            self.addLayerFactor(newDifferencesFactor)

            #// REVIEW: Does it make sense to have groups of one?   
            list = []   
            list.append(currentDifference)      
            outputVariablesGroup.append(list)
        

    def createTeamPerformanceToDifferenceFactor(self, strongerTeam, weakerTeam, output) :

        teams = (strongerTeam, weakerTeam)
        weights = (1.0, -1.0)
        return GaussianWeightedSumFactor(output, teams, weights)


    def createOutputVariable(self) :

        outputVariable = self.getParentFactorGraph().getVariableFactory().createBasicVariable("Team performance difference")
        return outputVariable
