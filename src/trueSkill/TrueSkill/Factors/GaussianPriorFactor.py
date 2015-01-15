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
