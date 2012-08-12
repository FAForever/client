from GaussianFactor import *


from copy import copy 

class GaussianLikelihoodFactor(GaussianFactor) :
    ''' Connects two variables and adds uncertainty.
    See the accompanying math paper for more details.
    '''
    def __init__(self, betaSquared, variable1, variable2):
    
        name = "Likelihood of %s going to %s" % (variable2, variable1)
        super(GaussianLikelihoodFactor, self).__init__(name)
        

        self._precision = 1.0/betaSquared
        self.createVariableToMessageBinding(variable1)
        self.createVariableToMessageBinding(variable2)


    def getLogNormalization(self) :

        vars = self.getVariables()
        messages = self.getMessages()

        return GaussianDistribution.logRatioNormalization( vars[0].getValue(), messages[0].getValue())


    def updateHelper(self, message1, message2, variable1, variable2) :
      
        message1Value = copy(message1.getValue())
        message2Value = copy(message2.getValue())
        
        marginal1 = copy(variable1.getValue())
        marginal2 = copy(variable2.getValue())

        a = self._precision/(self._precision + marginal2.getPrecision() - message2Value.getPrecision())

        newMessage = GaussianDistribution.fromPrecisionMean(
            a*(marginal2.getPrecisionMean() - message2Value.getPrecisionMean()),
            a*(marginal2.getPrecision() - message2Value.getPrecision()))

        oldMarginalWithoutMessage = GaussianDistribution.divide(marginal1, message1Value)

        newMarginal = GaussianDistribution.multiply(oldMarginalWithoutMessage, newMessage)

        # Update the message and marginal

        message1.setValue(newMessage)
        variable1.setValue(newMarginal)

        #Return the difference in the new marginal
        return GaussianDistribution.subtract(newMarginal, marginal1)
    

    def updateMessageIndex(self, messageIndex) :
    
        messages = self.getMessages()
        vars = self.getVariables()       

        if messageIndex == 0 :
            return self.updateHelper(messages[0], messages[1], vars[0], vars[1])
            
        elif messageIndex == 1 :
            return self.updateHelper(messages[1], messages[0], vars[1], vars[0])
        else :
            raise Exception()
