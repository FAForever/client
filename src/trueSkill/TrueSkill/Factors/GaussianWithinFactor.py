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





from copy import copy 

from math import sqrt

from trueSkill.TrueSkill.Factors.GaussianFactor import *
from trueSkill.TrueSkill.TruncatedGaussianCorrectionFunctions import *


class GaussianWithinFactor(GaussianFactor) :
    '''Factor representing a team difference that has not exceeded the draw margin.
        See the accompanying math paper for more details.
    '''
    def __init__(self, epsilon, variable):

        name = "%s <= %f" % (variable, epsilon)
        super(GaussianWithinFactor, self).__init__(name)
        self._epsilon = epsilon
        self.createVariableToMessageBinding(variable)


    def getLogNormalization(self) :

        variables = self.getVariables()
        marginal = variables[0].getValue()

        messages = self.getMessages()
        message = messages[0].getValue()
        messageFromVariable = GaussianDistribution.divide(marginal, message)
        mean = messageFromVariable.getMean()
        std = messageFromVariable.getStandardDeviation()
        z = GaussianDistribution.cumulativeTo((self._epsilon - mean)/std) - GaussianDistribution.cumulativeTo((-self._epsilon - mean)/std)

        return -GaussianDistribution.logProductNormalization(messageFromVariable, message) + log(z)


    def updateMessageVariable(self, message, variable) :

        oldMarginal = copy(variable.getValue())
        oldMessage = copy(message.getValue())
        messageFromVariable = GaussianDistribution.divide(oldMarginal, oldMessage)

        c = messageFromVariable.getPrecision()
        d = messageFromVariable.getPrecisionMean()

        sqrtC = sqrt(c)
        dOnSqrtC = d/sqrtC

        epsilonTimesSqrtC = self._epsilon*sqrtC
        d = messageFromVariable.getPrecisionMean()

        denominator = 1.0 - TruncatedGaussianCorrectionFunctions.wWithinMargin(dOnSqrtC, epsilonTimesSqrtC)
        newPrecision = c/denominator
        newPrecisionMean = (d +sqrtC*TruncatedGaussianCorrectionFunctions.vWithinMargin(dOnSqrtC, epsilonTimesSqrtC))/denominator

        newMarginal = GaussianDistribution.fromPrecisionMean(newPrecisionMean, newPrecision)
        newMessage = GaussianDistribution.divide(GaussianDistribution.multiply(oldMessage, newMarginal), oldMarginal)

        # Update the message and marginal
        message.setValue(newMessage)
        variable.setValue(newMarginal)

        # Return the difference in the new marginal
        return GaussianDistribution.subtract(newMarginal, oldMarginal)

