
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
