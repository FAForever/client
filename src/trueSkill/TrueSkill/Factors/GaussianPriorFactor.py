



from math import sqrt

from copy import copy 

from trueSkill.TrueSkill.Factors.GaussianFactor import *
from trueSkill.Numerics.GaussianDistribution import *

class GaussianPriorFactor(GaussianFactor) :
    
    def __init__(self, mean, variance, variable):

        name = "Prior value going to %s" % variable
        super(GaussianPriorFactor, self).__init__(name)
        

        msg = "message from %s to %s" % ( self, variable)
        self._newMessage = GaussianDistribution(mean, sqrt(variance))
        newMessage = Message(GaussianDistribution.fromPrecisionMean(0, 0), msg)

        self.createVariableToMessageBindingWithMessage(variable, newMessage)

    def updateMessageVariable(self, message, variable) :
        
        oldMarginal = copy(variable.getValue())
        oldMessage = message
        newMarginal = GaussianDistribution.fromPrecisionMean(oldMarginal.getPrecisionMean() + self._newMessage.getPrecisionMean() - oldMessage.getValue().getPrecisionMean(),
                oldMarginal.getPrecision() + self._newMessage.getPrecision() - oldMessage.getValue().getPrecision())

        variable.setValue(newMarginal)
        newMessage = self._newMessage
        message.setValue(newMessage)
        return GaussianDistribution.subtract(oldMarginal, newMarginal)
