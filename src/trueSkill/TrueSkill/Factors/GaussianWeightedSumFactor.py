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





from math import fabs

from copy import copy 
from GaussianFactor import *

class GaussianWeightedSumFactor(GaussianFactor) :
    def __init__(self, sumVariable, variablesToSum, variableWeights = None):

    
        name = self.createName(sumVariable, variablesToSum, variableWeights)
        super(GaussianWeightedSumFactor, self).__init__(name)
        
        self._variableIndexOrdersForWeights = []
        
        self._weights = []
        list = []
        self._weightsSquared = []
        self._weightsSquared.insert(0,list)
        self._variableIndexOrdersForWeights.insert(0,list)

#         The first weights are a straightforward copy
#         v_0 = a_1*v_1 + a_2*v_2 + ... + a_n * v_n

        variableWeightsLength = len(variableWeights)
        self._weights.insert(0,[0] * len(variableWeights))

        for i in range (variableWeightsLength) :

            weight = variableWeights[i]
            self._weights[0].insert(i,weight)
            self._weightsSquared[0].insert(i,square(weight))


        variablesToSumLength = len(variablesToSum)

        # 0..n-1
        self._variableIndexOrdersForWeights[0] = []
        
        for i in range (variablesToSumLength+1) :
            self._variableIndexOrdersForWeights[0].append(i)


        variableWeightsLength = len(variableWeights)

#         The rest move the variables around and divide out the constant.
#         For example:
#         v_1 = (-a_2 / a_1) * v_2 + (-a3/a1) * v_3 + ... + (1.0 / a_1) * v_0
#         By convention, we'll put the v_0 term at the end

        weightsLength = variableWeightsLength + 1
        
        
        for weightsIndex in range(1, weightsLength) :
            currentWeights = [0] * variableWeightsLength
            variableIndices = [0] * (variableWeightsLength + 1)

            variableIndices[0] = weightsIndex

            currentWeightsSquared = [0] * variableWeightsLength

#             keep a single variable to keep track of where we are in the array.
#             This is helpful since we skip over one of the spots
            currentDestinationWeightIndex = 0

            for currentWeightSourceIndex in range(variableWeightsLength) :

                if (currentWeightSourceIndex == (weightsIndex - 1)) :
                    continue

                currentWeight = (-variableWeights[currentWeightSourceIndex]/variableWeights[weightsIndex - 1])

                if (variableWeights[weightsIndex - 1] == 0) :
                    # HACK: Getting around division by zero
                    currentWeight = 0


                currentWeights[currentDestinationWeightIndex] = currentWeight
                currentWeightsSquared[currentDestinationWeightIndex] = currentWeight*currentWeight

                variableIndices[currentDestinationWeightIndex + 1] = currentWeightSourceIndex + 1
                currentDestinationWeightIndex = currentDestinationWeightIndex + 1


            # And the final one
            finalWeight = 1.0/variableWeights[weightsIndex - 1]

            if (variableWeights[weightsIndex - 1] == 0) :
                #HACK: Getting around division by zero
                finalWeight = 0;

            currentWeights[currentDestinationWeightIndex] = finalWeight
            currentWeightsSquared[currentDestinationWeightIndex] = square(finalWeight)
            variableIndices[len(variableWeights)] = 0
            self._variableIndexOrdersForWeights.append(variableIndices)

            self._weights.insert(weightsIndex, currentWeights)
            self._weightsSquared.insert(weightsIndex, currentWeightsSquared)


        self.createVariableToMessageBinding(sumVariable)

        for currentVariable in variablesToSum : 
            localCurrentVariable = currentVariable
            self.createVariableToMessageBinding(localCurrentVariable)


    def getLogNormalization(self) :
        
        vars = self.getVariables()
        messages = self.getMessages()

        result = 0.0

        # We start at 1 since offset 0 has the sum
        varCount = len(vars)
        
        for i in range(1,varCount) :
            result += GaussianDistribution.logRatioNormalization(vars[i].getValue(), messages[i].getValue())

        return result
    

    def updateHelper(self, weights, weightsSquared, messages, variables) :

        
  #         Potentially look at http://mathworld.wolfram.com/NormalSumDistribution.html for clues as
#         to what it's doing

        message0 = copy(messages[0].getValue())
        marginal0 = copy(variables[0].getValue())

       # The math works out so that 1/newPrecision = sum of a_i^2 /marginalsWithoutMessages[i]
        inverseOfNewPrecisionSum = 0.0
        anotherInverseOfNewPrecisionSum = 0.0
        weightedMeanSum = 0.0
        anotherWeightedMeanSum = 0.0

        weightsSquaredLength = len(weightsSquared)


        for i in range (weightsSquaredLength) :
           # These flow directly from the paper

            inverseOfNewPrecisionSum += weightsSquared[i]/(variables[i + 1].getValue().getPrecision() - messages[i + 1].getValue().getPrecision())

            diff = GaussianDistribution.divide(variables[i + 1].getValue(), messages[i + 1].getValue())
            anotherInverseOfNewPrecisionSum += weightsSquared[i]/diff.getPrecision()

            weightedMeanSum += weights[i] * (variables[i + 1].getValue().getPrecisionMean() - messages[i + 1].getValue().getPrecisionMean())  / (variables[i + 1].getValue().getPrecision() - messages[i + 1].getValue().getPrecision())

            anotherWeightedMeanSum += weights[i]*diff.getPrecisionMean()/diff.getPrecision()


        newPrecision = 1.0/inverseOfNewPrecisionSum;
        anotherNewPrecision = 1.0/anotherInverseOfNewPrecisionSum

        newPrecisionMean = newPrecision*weightedMeanSum
        anotherNewPrecisionMean = anotherNewPrecision*anotherWeightedMeanSum

        newMessage = GaussianDistribution.fromPrecisionMean(newPrecisionMean, newPrecision)
        oldMarginalWithoutMessage = GaussianDistribution.divide(marginal0, message0)

        newMarginal = GaussianDistribution.multiply(oldMarginalWithoutMessage, newMessage)

        # Update the message and marginal


        messages[0].setValue(newMessage)
        variables[0].setValue(newMarginal)
        

        # Return the difference in the new marginal
        finalDiff = GaussianDistribution.subtract(newMarginal, marginal0)
        return finalDiff;


    def updateMessageIndex(self, messageIndex) :
        
        allMessages = self.getMessages()
        allVariables = self.getVariables()

        Guard.argumentIsValidIndex(messageIndex, len(allMessages), "messageIndex")

        updatedMessages = []
        updatedVariables = []

        indicesToUse = self._variableIndexOrdersForWeights[messageIndex]

#         The tricky part here is that we have to put the messages and variables in the same
#         order as the weights. Thankfully, the weights and messages share the same index numbers,
#         so we just need to make sure they're consistent
        allMessagesCount = len(allMessages)
        
        for i in range (allMessagesCount) :
            updatedMessages.append(allMessages[indicesToUse[i]])
            updatedVariables.append(allVariables[indicesToUse[i]])

        
        return self.updateHelper(self._weights[messageIndex],
                                   self._weightsSquared[messageIndex],
                                   updatedMessages,
                                   updatedVariables)


    def createName(self, sumVariable, variablesToSum, weights) :

        # TODO: Perf? Use PHP equivalent of StringBuilder? implode on arrays?
        result = str(sumVariable)
        
        result = result + ' = '
        
        totalVars = len(variablesToSum)
        
        for i in range (totalVars) :
            isFirst = False
            if (i == 0) :
                isFirst = True

            if(isFirst and (weights[i] < 0)) :
                result = result + '-'


            absValue = "%f" % (fabs(weights[i])) # 0.00?
            result = result + absValue
            result = result + "*["
            result = result + str(variablesToSum[i])
            result = result + ']'
            
            isLast = False
            if i == totalVars - 1 :
                isLast = True 
            
            if not isLast :

                if(weights[i + 1] >= 0) :

                    result = result + ' + '

                else :

                    result = result + ' - '
        return result
