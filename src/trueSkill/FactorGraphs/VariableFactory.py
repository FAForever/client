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





from Variable import Variable, KeyedVariable


class VariableFactory (object):

    def __init__(self, variablePriorInitializer):
        
       
        #using a Func<TValue> to encourage fresh copies in case it's overwritten    
        self._variablePriorInitializer = variablePriorInitializer
        
    def createBasicVariable(self, name) :
        initializer = self._variablePriorInitializer
        newVar = Variable(name, initializer())
        return newVar


    def createKeyedVariable(self, key, name) :
        
        initializer = self._variablePriorInitializer
        newVar = KeyedVariable(key, name, initializer())
        
        return newVar
    
