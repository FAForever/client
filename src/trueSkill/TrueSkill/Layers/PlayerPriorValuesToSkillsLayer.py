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
from trueSkill.TrueSkill.Factors.GaussianPriorFactor import *
from trueSkill.Numerics.BasicMath import *

# We intentionally have no Posterior schedule since the only purpose here is to
# start the process.
class PlayerPriorValuesToSkillsLayer(TrueSkillFactorGraphLayer) :
    def __init__(self, parentGraph, teams):
        super(PlayerPriorValuesToSkillsLayer, self).__init__(parentGraph)

        self._teams = teams

    def buildLayer(self) :

        teams = self._teams


        for currentTeam in teams :

            localCurrentTeam = currentTeam
            currentTeamSkills = []

            currentTeamAllPlayers = localCurrentTeam.getAllPlayers()
            # print "currentTeamAllPlayers"
            # print currentTeamAllPlayers

            for currentTeamPlayer in currentTeamAllPlayers :

                localCurrentTeamPlayer = currentTeamPlayer
                currentTeamPlayerRating = currentTeam.getRating(localCurrentTeamPlayer)
                # print "currentTeamPlayerRating"


                playerSkill = self.createSkillOutputVariable(localCurrentTeamPlayer)


                priorFactor = self.createPriorFactor(localCurrentTeamPlayer, currentTeamPlayerRating, playerSkill)

                self.addLayerFactor(priorFactor)
                currentTeamSkills.append(playerSkill)


            outputVariablesGroups = self.getOutputVariablesGroups()

            outputVariablesGroups.append(currentTeamSkills)

    def getPriorScheduleStep(self, prior):

        return ScheduleStep("Prior to Skill Step", prior, 0)

    def createPriorSchedule(self) :

        localFactors = self.getLocalFactors()
        return self.scheduleSequence(map(self.getPriorScheduleStep, localFactors), "All priors")


    def createPriorFactor(self, player, priorRating, skillsVariable) :

        prior = GaussianPriorFactor(priorRating.getMean(),
                                       square(priorRating.getStandardDeviation()) +
                                       square(self.getParentFactorGraph().getGameInfo().getDynamicsFactor()),
                                       skillsVariable)
        return prior

    def createSkillOutputVariable(self, key) :

        parentFactorGraph = self.getParentFactorGraph()
        variableFactory = parentFactorGraph.getVariableFactory()
        skillOutputVariable = variableFactory.createKeyedVariable(key, str(key) + "'s skill")
        # print "skillOutputVariable"
        # print skillOutputVariable
        return skillOutputVariable
