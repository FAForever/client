



from trueSkill.TrueSkill.Layers.TrueSkillFactorGraphLayer import *

from trueSkill.TrueSkill.Factors.GaussianLikelihoodFactor import *

from trueSkill.Numerics.BasicMath import *

class PlayerSkillsToPerformancesLayer(TrueSkillFactorGraphLayer) :
    def __init__(self, parentGraph) :
        super(PlayerSkillsToPerformancesLayer, self).__init__(parentGraph)

    def buildLayer(self) :


        inputVariablesGroups = self.getInputVariablesGroups()
        outputVariablesGroups = self.getOutputVariablesGroups()

        for currentTeam in inputVariablesGroups :
            currentTeamPlayerPerformances = []
            for playerSkillVariable in currentTeam :

                localPlayerSkillVariable = playerSkillVariable
                
                
                currentPlayer = localPlayerSkillVariable.getKey()
                playerPerformance = self.createOutputVariable(currentPlayer)
                newLikelihoodFactor = self.createLikelihood(localPlayerSkillVariable, playerPerformance)
                self.addLayerFactor(newLikelihoodFactor)
                currentTeamPlayerPerformances.append(playerPerformance)

            
            outputVariablesGroups.append(currentTeamPlayerPerformances)


    def createLikelihood(self, playerSkill, playerPerformance) :
        return GaussianLikelihoodFactor(square(self.getParentFactorGraph().getGameInfo().getBeta()), playerPerformance, playerSkill)


    def createOutputVariable(self, key) :
        outputVariable = self.getParentFactorGraph().getVariableFactory().createKeyedVariable(key, str(key)+ "'s performance")
        return outputVariable


    def getSkillToPerfstep(self, likelihood) :
        return  ScheduleStep("Skill to Perf step", likelihood, 0)

    def createPriorSchedule(self) :

        localFactors = self.getLocalFactors()
        return self.scheduleSequence(
                                     map(self.getSkillToPerfstep, localFactors),
                                      "All skill to performance sending")


    def getName(self, likelihood):
        return ScheduleStep("name", likelihood, 1)

    def createPosteriorSchedule(self) :
    
        localFactors = self.getLocalFactors()
        return self.scheduleSequence(map(self.getName, localFactors),  "Post All skill to performance sending")
