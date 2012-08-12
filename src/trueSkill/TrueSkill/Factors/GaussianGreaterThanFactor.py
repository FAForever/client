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
    