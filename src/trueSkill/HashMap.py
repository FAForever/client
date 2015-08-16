



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
