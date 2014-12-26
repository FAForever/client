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





from trueSkill.PartialPlay import *
from trueSkill.TrueSkill.Layers.TrueSkillFactorGraphLayer import *
from trueSkill.TrueSkill.Factors.GaussianWeightedSumFactor import *

class PlayerPerformancesToTeamPerformancesLayer(TrueSkillFactorGraphLayer) :
    
    def __init__(self, parentGraph):
        super(PlayerPerformancesToTeamPerformancesLayer, self).__init__(parentGraph)

    def buildLayer(self) :

        inputVariablesGroups = self.getInputVariablesGroups()
        for currentTeam in inputVariablesGroups : 

            localCurrentTeam = currentTeam
            teamPerformance = self.createOutputVariable(localCurrentTeam)

            newSumFactor = self.createPlayerToTeamSumFactor(localCurrentTeam, teamPerformance)
            
            self.addLayerFactor(newSumFactor)

            #// REVIEW: Does it make sense to have groups of one?
            

            outputVariablesGroups = self.getOutputVariablesGroups()
            list = []   
            list.append(teamPerformance)      
            outputVariablesGroups.append(list)


    def PerftoTeamPerfStep(self, weightedSumFactor):

        return ScheduleStep("Perf to Team Perf Step", weightedSumFactor, 0)

    def createPriorSchedule(self) :
    
        localFactors = self.getLocalFactors()

        sequence = self.scheduleSequence(map(self.PerftoTeamPerfStep, localFactors),
                                            "all player perf to team perf schedule")
        

        return sequence
    

    def partialPlayPercentage(self, v):
         player = v.getKey()
         return PartialPlay.getPartialPlayPercentage(player)

    def createPlayerToTeamSumFactor(self, teamMembers, sumVariable) :
       
        weights = map(self.partialPlayPercentage, teamMembers)

        return  GaussianWeightedSumFactor( sumVariable,
                                           teamMembers,
                                           weights)
                                                 


    def createPosteriorSchedule(self) :
          
        allFactors = []
        localFactors = self.getLocalFactors()
        
        for currentFactor in localFactors :

            localCurrentFactor = currentFactor
            numberOfMessages = localCurrentFactor.getNumberOfMessages()

            for currentIteration in range(1, numberOfMessages) :


                allFactors.append(ScheduleStep("------------------ team sum perf @" + str(currentIteration),
                                                 localCurrentFactor, currentIteration))

        return self.scheduleSequence(allFactors, "***************************** all of the team's sum iterations")


    def currentPlayetgetKey(self, currentPlayer):
        return str((currentPlayer.getKey()))

    def createOutputVariable(self, team) :

        memberNames = map(self.currentPlayetgetKey,team)
        

        teamMemberNames = ", ".join(memberNames)

        outputVariable = self.getParentFactorGraph().getVariableFactory().createBasicVariable("Team[" + teamMemberNames + "]'s performance")
        return outputVariable
