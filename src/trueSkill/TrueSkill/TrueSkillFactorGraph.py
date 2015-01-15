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





from math import exp
from trueSkill.FactorGraphs.FactorGraph import *
from trueSkill.FactorGraphs.FactorList import *
from trueSkill.TrueSkill.Layers.PlayerPriorValuesToSkillsLayer import *
from trueSkill.Numerics.GaussianDistribution import *
from trueSkill.TrueSkill.Layers.PlayerSkillsToPerformancesLayer import *
from trueSkill.TrueSkill.Layers.TeamPerformancesToTeamPerformanceDifferencesLayer import *
from trueSkill.TrueSkill.Layers.PlayerPerformancesToTeamPerformancesLayer import  *
from trueSkill.TrueSkill.Layers.IteratedTeamDifferencesInnerLayer import *
from trueSkill.TrueSkill.Layers.TeamDifferencesComparisonLayer import *
from trueSkill.RatingContainer import *

class ReversableList(list):
    def reverse(self):
        return list(reversed(self))



class TrueSkillFactorGraph(FactorGraph) :
    def __init__(self, gameInfo, teams, teamRanks):


        self._priorLayer = PlayerPriorValuesToSkillsLayer(self, teams)
        self._gameInfo = gameInfo
        newFactory = VariableFactory(self.fromPrecisionMean)
                                        
        self.setVariableFactory(newFactory)
        self._layers = [
                              self._priorLayer,
                              PlayerSkillsToPerformancesLayer(self),
                              PlayerPerformancesToTeamPerformancesLayer(self),
                              IteratedTeamDifferencesInnerLayer(
                                  self,
                                  TeamPerformancesToTeamPerformanceDifferencesLayer(self),
                                  TeamDifferencesComparisonLayer(self, teamRanks))
                              ]

    def fromPrecisionMean(self):
        return GaussianDistribution.fromPrecisionMean(0, 0)


    def getGameInfo(self) :
        return self._gameInfo


    def buildGraph(self) :
        

        
        lastOutput = None

        layers = self._layers

        for currentLayer in layers :
            
                 
            if (lastOutput != None) :
                
                currentLayer.setInputVariablesGroups(lastOutput)

            currentLayer.buildLayer()

            lastOutput = currentLayer.getOutputVariablesGroups()
            

    def runSchedule(self) :
        
        fullSchedule = self.createFullSchedule()
        fullScheduleDelta = fullSchedule.visit()



    def getProbabilityOfRanking(self) :

        factorList = FactorList()


        layers = self._layers
        for currentLayer in layers :
            
            localFactors = currentLayer.getLocalFactors()
            for currentFactor in localFactors :
                localCurrentFactor = currentFactor
                factorList.addFactor(localCurrentFactor)


        logZ = factorList.getLogNormalization()

        return exp(logZ)


    def createFullSchedule(self) :

        fullSchedule = []

        layers = self._layers
        for currentLayer in layers :



            currentPriorSchedule = currentLayer.createPriorSchedule()
            
            if currentPriorSchedule != None :
                fullSchedule.append(currentPriorSchedule)

        allLayersReverse = ReversableList(self._layers)

        for currentLayer in allLayersReverse.reverse() :
            
            currentPosteriorSchedule = currentLayer.createPosteriorSchedule()
            if (currentPosteriorSchedule != None) :

                fullSchedule.append(currentPosteriorSchedule)

        return ScheduleSequence("Full schedule", fullSchedule)

    def getUpdatedRatings(self) :

        result = RatingContainer()

        priorLayerOutputVariablesGroups = self._priorLayer.getOutputVariablesGroups()
        
    
        for currentTeam in priorLayerOutputVariablesGroups :
            for currentPlayer in currentTeam :

                localCurrentPlayer = currentPlayer.getKey()  
                newRating = Rating(currentPlayer.getValue().getMean(),
                                        currentPlayer.getValue().getStandardDeviation())
                
                result.setRating(localCurrentPlayer, newRating)
        return result

