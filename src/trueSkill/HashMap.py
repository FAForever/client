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





import hashlib


class HashMap(object):
    '''
    Basic hashmap that supports object keys.
    '''
    def __init__(self):
        self._hashToValue = {}
        self._hashToKey = {}

    def getValue(self, key) :
        hash = self.__getHash(key)
        hashValue = self._hashToValue[hash];
        return hashValue

    def setValue(self, key, value) :
        hash = self.__getHash(key)
        self._hashToKey[hash] = key
        self._hashToValue[hash] = value
        return self


    def getAllKeys(self) :

        keys = self._hashToKey
        result = []
        for key in keys :
            result.append(key)
        return result


    def getAllValues(self) :
        values = self._hashToValue

        result = []
        for key in values :
            result.append(values[key])
        return result


    def count(self) :
        return len(self._hashToKey)


    def __getHash(self, key) :
        return key
