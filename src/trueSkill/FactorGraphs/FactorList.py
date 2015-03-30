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





class FactorList(object) :
    
    def __init__(self) :
    
        self._list = []

    def getLogNormalization(self) :

        list = self._list
        for currentFactor in list :

            currentFactor.resetMarginals()

        sumLogZ = 0.0

        listCount = len(self._list)

        for i in range (listCount) :

            f = self._list[i]

            numberOfMessages = f.getNumberOfMessages()

            for j in range (numberOfMessages) :

                sumLogZ = sumLogZ + f.sendMessageIndex(j)


        sumLogS = 0.0

        for currentFactor in list :

            sumLogS = sumLogS + currentFactor.getLogNormalization()
 
        return sumLogZ + sumLogS


    def count(self) :
        return len(self._list)


    def addFactor(self, factor) :

        self._list.append(factor)
        return factor
    
