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





from sys import maxint

class Range(object):
    '''The whole purpose of this class is to make the code for the SkillCalculator(s)
    look a little cleaner
    '''
    def __init__(self, min, max) :
        
        if min > max :
            raise Exception("min > max")
        
        self._min = min
        self._max = max
        
    def getMin(self):
        return self._min
    
    def getMax(self):
        return self._max
    

    
    @staticmethod
    def inclusive(min, max):
        return Range(min, max)
    
    @staticmethod
    def exactly(value):
        return Range(value, value)

   
    @staticmethod
    def atLeast(minimumValue) :
        return Range(minimumValue, maxint)
    
    #@staticmethod
    def isInRange(self, value):
        if self._min <= value and value <= self._max :
            return 1
        return 0
             
