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

