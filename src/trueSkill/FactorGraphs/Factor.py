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





from trueSkill.Guard import Guard
from trueSkill.HashMap import *
from trueSkill.FactorGraphs.Message import *
from trueSkill.FactorGraphs.Variable import *


class Factor (object):
    def __init__(self, name):
        
        self._messages = []
        self._name = "Factor[%s]" % name
        self._variables = []
        self._messageToVariableBinding = HashMap()
        


    def getLogNormalization(self) :
        '''return The log-normalization constant of that factor'''
        return 0
    
    
    def getNumberOfMessages(self) :
        '''@return The number of messages that the factor has'''

        return len(self._messages)
    
    def getVariables(self) :
        return self._variables

    def getMessages(self) :
        return self._messages

    def updateMessageIndex(self, messageIndex) :
        '''Update the message and marginal of the i-th variable that the factor is connected to'''
        Guard.argumentIsValidIndex(messageIndex, len(self._messages), "messageIndex")
        message = self._messages[messageIndex]
        variable = self._messageToVariableBinding.getValue(message)  
        return self.updateMessageVariable(message, variable)

    def updateMessageVariable(self, message, variable) :
        raise Exception()
    
    def resetMarginals(self) :
        ''' Resets the marginal of the variables a factor is connected to'''
        allValues = self._messageToVariableBinding.getAllValues()
        for currentVariable in allValues:
            currentVariable.resetToPrior()

    def sendMessageIndex(self, messageIndex) :
        '''Sends the ith message to the marginal and returns the log-normalization constant'''
        Guard.argumentIsValidIndex(messageIndex, len(self._messages), "messageIndex")
        message = self._messages[messageIndex]
        variable = self._messageToVariableBinding.getValue(message)
        return self.sendMessageVariable(message, variable)

    def sendMessageVariable(self, message, variable) :
        pass

    def createVariableToMessageBinding(self, variable) :
        pass
    
    def createVariableToMessageBindingWithMessage(self, variable, message) :
        index = len(self._messages)
        localMessages = self._messages
        localMessages.append(message)
        self._messageToVariableBinding.setValue(message, variable)
        localVariables = self._variables
        localVariables.append(variable)
        return message

    def __str__(self):
        if self._name != None :
            return self._name



