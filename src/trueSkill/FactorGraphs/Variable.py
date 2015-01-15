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





import time

class Variable(object):
    def __init__(self, name, prior):
        
        self._name = "Variable[%s]" % name
        self._prior = prior
        self._value = self._prior

        
    def getValue(self):
        return self._value

    def setValue(self, value):

#        print self._name
#
#        print value
        self._value = value
        
    def resetToPrior(self):
        self._value = self._prior
#
    def __str__(self):
        return self._name
    

class DefaultVariable(Variable):
    def __init__(self):
        super(DefaultVariable, self).__init__("Default", None)
        

    def getValue(self):
        return 0
    
    def setValue(self, value):
        raise Exception()

    
    
class KeyedVariable(Variable):
    def __init__(self, key, name, prior):
        super(KeyedVariable, self).__init__(name, prior)

        self._key = key

    def getKey(self) :
        key = self._key
        return key
    
