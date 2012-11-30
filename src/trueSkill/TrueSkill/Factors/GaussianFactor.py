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
