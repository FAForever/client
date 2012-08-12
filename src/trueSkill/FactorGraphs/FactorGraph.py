
from VariableFactory import VariableFactory

class FactorGraph(object):
    def __init__(self):
        self._variableFactory = None

    def getVariableFactory(self) :
        return self._variableFactory


    def setVariableFactory(self, factory) :
        self._variableFactory = factory
