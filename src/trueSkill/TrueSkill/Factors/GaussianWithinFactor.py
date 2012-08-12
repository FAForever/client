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

