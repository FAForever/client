



from Rating import *

DEFAULT_BETA = 250 # Default initial mean / 6
DEFAULT_DRAW_PROBABILITY = 0.10
DEFAULT_DYNAMICS_FACTOR = 5 # Default initial mean / 300
DEFAULT_INITIAL_MEAN = 1500
DEFAULT_INITIAL_STANDARD_DEVIATION = 500 # Default initial mean / 3

## CHESS VALUES

#InitialMean = 1500
#InitialStandardDeviation = 500
#Beta = 250
#DynamicsFactor/Tau= 5
#Draw Probability = 0.04

class GameInfo(object):
    '''' Parameters about the game for calculating the TrueSkill.'''
    def __init__(self,
                 initialMean = DEFAULT_INITIAL_MEAN,
                 initialStandardDeviation = DEFAULT_INITIAL_STANDARD_DEVIATION, 
                 beta = DEFAULT_BETA, 
                 dynamicsFactor = DEFAULT_DYNAMICS_FACTOR, 
                 drawProbability = DEFAULT_DRAW_PROBABILITY                 
                 ) :


        self._initialMean = initialMean
        self._initialStandardDeviation = initialStandardDeviation
        self._beta = beta
        self._dynamicsFactor = dynamicsFactor
        self._drawProbability = drawProbability
  
    

    def getInitialMean(self) :
        return self._initialMean
    
    
    def getInitialStandardDeviation(self) :
        return self._initialStandardDeviation

    
    def getBeta(self) :
        return self._beta

    def getDynamicsFactor(self) :
        return self._dynamicsFactor
    
    def getDrawProbability(self) :
        return self._drawProbability

    def getDefaultRating(self) :
        return Rating(self._initialMean, self._initialStandardDeviation)
