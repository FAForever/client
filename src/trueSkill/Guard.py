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





class Guard(object):
    @staticmethod
    def argumentNotNull( value, parameterName) :
        if value == '' :
            raise Exception(parameterName, " can not be null")
    @staticmethod
    def argumentIsValidIndex( index, count, parameterName) :
        if index < 0 or index >= count :
            raise Exception(parameterName, " is an invalid index")
    
    @staticmethod
    def argumentInRangeInclusive( value, min, max, parameterName) :
        if value < min or value > max :
            raise Exception(parameterName, " is not in the valid range [" + min + ", " + max + "]")
    
