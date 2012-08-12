from Factor import Factor
from FactorGraph import FactorGraph
from Schedule import Schedule, ScheduleStep, ScheduleSequence

class FactorGraphLayer(object):
    def __init__(self, parentGraph):
        self._localFactors = []
        self._outputVariablesGroups = []   
        self._inputVariablesGroups = []
        self._parentFactorGraph = parentGraph

    def getInputVariablesGroups(self) :
        inputVariablesGroups = self._inputVariablesGroups
        return inputVariablesGroups

    def getParentFactorGraph(self) :
        parentFactorGraph = self._parentFactorGraph
        return parentFactorGraph

    def getOutputVariablesGroups(self) :
        outputVariablesGroups = self._outputVariablesGroups
        return outputVariablesGroups
    
    def getLocalFactors(self) :
        localFactors = self._localFactors
        return localFactors

    def setInputVariablesGroups(self, value) :
        self._inputVariablesGroups = value

    def scheduleSequence(self, itemsToSequence, name) :
        return ScheduleSequence(name, itemsToSequence)

    def addLayerFactor(self, factor) :
        self._localFactors.append(factor)

    def createPriorSchedule(self) :
        return None
    
    def createPosteriorSchedule(self) :
        return None

