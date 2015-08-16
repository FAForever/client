



from trueSkill.TrueSkill.Layers.TrueSkillFactorGraphLayer import *
from trueSkill.FactorGraphs.Schedule import *

class IteratedTeamDifferencesInnerLayer(TrueSkillFactorGraphLayer) :
    def __init__(self, parentGraph, teamPerformancesToPerformanceDifferences, teamDifferencesComparisonLayer):
        
        super(IteratedTeamDifferencesInnerLayer, self).__init__(parentGraph)
        
        self._TeamDifferencesComparisonLayer = teamDifferencesComparisonLayer
        self._TeamPerformancesToTeamPerformanceDifferencesLayer = teamPerformancesToPerformanceDifferences

    def getLocalFactors(self) :

        localFactors = []
        localFactors.extend(self._TeamPerformancesToTeamPerformanceDifferencesLayer.getLocalFactors())
        localFactors.extend(self._TeamDifferencesComparisonLayer.getLocalFactors())

        return localFactors


    def buildLayer(self) :
    
        inputVariablesGroups = self.getInputVariablesGroups()
        self._TeamPerformancesToTeamPerformanceDifferencesLayer.setInputVariablesGroups(inputVariablesGroups)
        self._TeamPerformancesToTeamPerformanceDifferencesLayer.buildLayer()

        teamDifferencesOutputVariablesGroups = self._TeamPerformancesToTeamPerformanceDifferencesLayer.getOutputVariablesGroups()
        self._TeamDifferencesComparisonLayer.setInputVariablesGroups(teamDifferencesOutputVariablesGroups)
        
        
        self._TeamDifferencesComparisonLayer.buildLayer()


    def createPriorSchedule(self) :
        
        case = len(self.getInputVariablesGroups())

        if  case == 1 :
                raise InvalidOperationException()
        elif  case == 2 :
                loop = self.createTwoTeamInnerPriorLoopSchedule()

        else :
                loop = self.createMultipleTeamInnerPriorLoopSchedule()


        # When dealing with differences, there are always (n-1) differences, so add in the 1
        totalTeamDifferences = len(self._TeamPerformancesToTeamPerformanceDifferencesLayer.getLocalFactors())
        totalTeams = totalTeamDifferences + 1

        localFactors = self._TeamPerformancesToTeamPerformanceDifferencesLayer.getLocalFactors()

        firstDifferencesFactor = localFactors[0]
        lastDifferencesFactor = localFactors[totalTeamDifferences - 1]

        
        array = (loop,ScheduleStep("teamPerformanceToPerformanceDifferenceFactors[0] @ 1", 
                                   firstDifferencesFactor, 1), 
                                   ScheduleStep("teamPerformanceToPerformanceDifferenceFactors[teamTeamDifferences = %d - 1] @ 2" % totalTeamDifferences, 
                                   lastDifferencesFactor, 
                                   2)
                                   )
        
        
        innerSchedule = ScheduleSequence("inner schedule", array)

        return innerSchedule


    def createTwoTeamInnerPriorLoopSchedule(self) :

        teamPerformancesToTeamPerformanceDifferencesLayerLocalFactors = self._TeamPerformancesToTeamPerformanceDifferencesLayer.getLocalFactors()
        teamDifferencesComparisonLayerLocalFactors = self._TeamDifferencesComparisonLayer.getLocalFactors()

        firstPerfToTeamDiff = teamPerformancesToTeamPerformanceDifferencesLayerLocalFactors[0]
        firstTeamDiffComparison = teamDifferencesComparisonLayerLocalFactors[0]
        
        itemsToSequence =  (
                    ScheduleStep(
                        "send team perf to perf differences",
                        firstPerfToTeamDiff,
                        0),
                    ScheduleStep(
                        "send to greater than or within factor",
                        firstTeamDiffComparison,
                        0)
                )


        return self.scheduleSequence(
            itemsToSequence,
            "loop of just two teams inner sequence")
    

    def createMultipleTeamInnerPriorLoopSchedule(self) :
 
        totalTeamDifferences = len(self._TeamPerformancesToTeamPerformanceDifferencesLayer.getLocalFactors())

        forwardScheduleList = []

        for i in range(totalTeamDifferences - 1) :

            teamPerformancesToTeamPerformanceDifferencesLayerLocalFactors = self._TeamPerformancesToTeamPerformanceDifferencesLayer.getLocalFactors()
            teamDifferencesComparisonLayerLocalFactors = self._TeamDifferencesComparisonLayer.getLocalFactors()

            currentTeamPerfToTeamPerfDiff = teamPerformancesToTeamPerformanceDifferencesLayerLocalFactors[i]
            currentTeamDiffComparison = teamDifferencesComparisonLayerLocalFactors[i]

            currentForwardSchedulePiece = self.scheduleSequence(
                            [
                                ScheduleStep(
                                ("team perf to perf diff %d" % i),
                                currentTeamPerfToTeamPerfDiff, 0),
                                ScheduleStep(
                                ("greater than or within result factor %d" % i),
                                currentTeamDiffComparison, 0),
                                ScheduleStep(
                                ("team perf to perf diff factors [%d], 2" % i),
                                currentTeamPerfToTeamPerfDiff, 2)
                        ], ("current forward schedule piece : " + str(i)))

            forwardScheduleList.append(currentForwardSchedulePiece)


        forwardSchedule = ScheduleSequence("forward schedule", forwardScheduleList)


        backwardScheduleList = []


        for i in range (totalTeamDifferences - 1) :

            teamPerformancesToTeamPerformanceDifferencesLayerLocalFactors = self._TeamPerformancesToTeamPerformanceDifferencesLayer.getLocalFactors()
            teamDifferencesComparisonLayerLocalFactors = self._TeamDifferencesComparisonLayer.getLocalFactors()

            differencesFactor = teamPerformancesToTeamPerformanceDifferencesLayerLocalFactors[totalTeamDifferences - 1 - i]
            comparisonFactor = teamDifferencesComparisonLayerLocalFactors[totalTeamDifferences - 1 - i]
            performancesToDifferencesFactor = teamPerformancesToTeamPerformanceDifferencesLayerLocalFactors[totalTeamDifferences - 1 - i]

            currentBackwardSchedulePiece = ScheduleSequence(
                "current backward schedule piece",
                (
                         ScheduleStep(
                            ("teamPerformanceToPerformanceDifferenceFactors[totalTeamDifferences - 1 - %d] @ 0" % i),
                            differencesFactor, 0),
                         ScheduleStep(
                            ("greaterThanOrWithinResultFactors[totalTeamDifferences - 1 - %d] @ 0"% i),
                            comparisonFactor, 0),
                         ScheduleStep(
                            ("teamPerformanceToPerformanceDifferenceFactors[totalTeamDifferences - 1 - %d] @ 1" % i),
                            performancesToDifferencesFactor, 1)
                ))
            backwardScheduleList.append(currentBackwardSchedulePiece)
        

        backwardSchedule =  ScheduleSequence("backward schedule", backwardScheduleList)

        forwardBackwardScheduleToLoop =  ScheduleSequence(
                "forward Backward Schedule To Loop",
                (forwardSchedule, backwardSchedule))

        initialMaxDelta = 0.0001

        loop = ScheduleLoop(
            ("loop with max delta of %f" % initialMaxDelta),
            forwardBackwardScheduleToLoop,
            initialMaxDelta)

        return loop


