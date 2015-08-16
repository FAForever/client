



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
    
