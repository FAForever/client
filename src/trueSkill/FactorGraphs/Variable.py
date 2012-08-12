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
    
