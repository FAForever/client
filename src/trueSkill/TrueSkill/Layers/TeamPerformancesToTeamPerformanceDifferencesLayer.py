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
