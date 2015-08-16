



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
             
