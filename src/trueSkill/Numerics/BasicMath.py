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





# Basic math functions.

def square(x):
    '''
     Squares the input (x^2 = x * x)
      @param number $x Value to square (x)
     @return number The squared value (x^2)
    '''

    return x ** 2

def sumArray(itemsToSum, callback) :
    '''
     Sums the items in $itemsToSum
     @param array $itemsToSum The items to sum,
     @param callback $callback The function to apply to each array element before summing.
     @return number The sum.
'''

    mappedItems = map(callback, itemsToSum)
    return sum(mappedItems)

