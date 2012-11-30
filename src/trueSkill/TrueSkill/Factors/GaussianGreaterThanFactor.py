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





from trueSkill.FactorGraphs.Message import *
from trueSkill.FactorGraphs.Variable import *
from trueSkill.Numerics.GaussianDistribution import *
from trueSkill.TrueSkill.TruncatedGaussianCorrectionFunctions import *
from trueSkill.TrueSkill.Factors.GaussianFactor import *

from math import log, sqrt
from copy import copy 

class GaussianGreaterThanFactor(GaussianFactor) :
    def __init__(self, epsilon, variable ):
        msg = "%s > %f" % (variable, epsilon)
        super(GaussianGreaterThanFactor, self).__init__(msg)
        
        self._epsilon = epsilon
        self.createVariableToMessageBinding(variable)
        
    def getLogNormalization(self) :

        vars = self.getVariables()
        marginal = vars[0].getValue()
        messages = self.getMessages()
        message = messages[0].getValue()
        messageFromVariable = GaussianDistribution.divide(marginal, message)
        return -GaussianDistribution.logProductNormalization(messageFromVariable, message) + log(
                   GaussianDistribution.cumulativeTo((messageFromVariable.getMean() - self._epsilon)/
                                                     messageFromVariable.getStandardDeviation()))

    def updateMessageVariable(self, message, variable) :

        oldMarginal = copy(variable.getValue())
        oldMessage = copy(message.getValue())
        messageFromVar = GaussianDistribution.divide(oldMarginal, oldMessage)

        c = messageFromVar.getPrecision()
        d = messageFromVar.getPrecisionMean()

        sqrtC = sqrt(c)

        dOnSqrtC = d/sqrtC;

        epsilsonTimesSqrtC = self._epsilon*sqrtC
        d = messageFromVar.getPrecisionMean()

        denom = 1.0 - TruncatedGaussianCorrectionFunctions.wExceedsMargin(dOnSqrtC, epsilsonTimesSqrtC)

        newPrecision = c/denom
        newPrecisionMean = (d +
                             sqrtC*
                             TruncatedGaussianCorrectionFunctions.vExceedsMargin(dOnSqrtC, epsilsonTimesSqrtC)) / denom

        newMarginal = GaussianDistribution.fromPrecisionMean(newPrecisionMean, newPrecision)

        newMessage = GaussianDistribution.divide(
                              GaussianDistribution.multiply(oldMessage, newMarginal),
                              oldMarginal)

        # Update the message and marginal
        message.setValue(newMessage)

        variable.setValue(newMarginal)

        #// Return the difference in the new marginal
        return GaussianDistribution.subtract(newMarginal, oldMarginal)
    
