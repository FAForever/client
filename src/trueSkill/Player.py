



from Guard import *


#/**
# * Represents a player who has a Rating.


DEFAULT_PARTIAL_PLAY_PERCENTAGE = 1.0  #// = 100% play time
DEFAULT_PARTIAL_UPDATE_PERCENTAGE = 1.0 # // = receive 100% update
# */
class Player(object):
    def __init__(self, 
                 id, 
                 partialPlayPercentage=DEFAULT_PARTIAL_PLAY_PERCENTAGE, 
                 partialUpdatePercentage=DEFAULT_PARTIAL_UPDATE_PERCENTAGE) :


        # If they don't want to give a player an id, that's ok...
        Guard.argumentInRangeInclusive(partialPlayPercentage, 0.0, 1.0, "partialPlayPercentage")
        Guard.argumentInRangeInclusive(partialUpdatePercentage, 0, 1.0, "partialUpdatePercentage")
        self._Id = id
        self._PartialPlayPercentage = partialPlayPercentage
        self._PartialUpdatePercentage = partialUpdatePercentage


#    /**
#     * The identifier for the player, such as a name.
#     */
    def getId(self) :

        return self._Id;
    
    
#    /**
#     * Indicates the percent of the time the player should be weighted where 0.0 indicates the player didn't play and 1.0 indicates the player played 100% of the time.
#     */
    def getPartialPlayPercentage(self) :
        return self._PartialPlayPercentage

    
#    /**
#     * Indicated how much of a skill update a player should receive where 0.0 represents no update and 1.0 represents 100% of the update.
#     */
    def  getPartialUpdatePercentage(self) :
        return self._PartialUpdatePercentage

    
    def __str__(self) :
        if (self._Id != None) :
            return str(self._Id)

