from trueSkill.FactorGraphs.Factor import *

from trueSkill.Numerics.GaussianDistribution import *
class GaussianFactor(Factor) :
    
    def __init__(self, name):
        super(GaussianFactor, self).__init__(name)

    def sendMessageVariable(self, message, variable) :
        ''' Sends the factor-graph message with and returns the log-normalization constant.'''
        marginal = variable.getValue()
        messageValue = message.getValue()
        logZ = GaussianDistribution.logProductNormalization(marginal, messageValue)
        variable.setValue(GaussianDistribution.multiply(marginal, messageValue))
        return logZ
    

    def createVariableToMessageBinding(self, variable) :
        newDistribution = GaussianDistribution.fromPrecisionMean(0.0, 0.0)
        binding = self.createVariableToMessageBindingWithMessage(variable,
                                                      Message(
                                                          newDistribution,
                                                          ("message from %s to %s") % (self, variable)))
        return binding
