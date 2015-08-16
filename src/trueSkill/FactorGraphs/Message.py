



class Message(object):
    def __init__(self, value = '', name = ''):

        self._name = name        
        self._value = value


    def getValue(self) :
        value = self._value
        return value


    def setValue(self, value) :
        self._value = value

    def __str__(self) :
        return self._name
