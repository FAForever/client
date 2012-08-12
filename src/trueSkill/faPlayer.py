from Rating import *
from Player import *
from RatingContainer import *

class faPlayer(RatingContainer) :
    def __init__(self, player = None, rating = None):
    
        super(faPlayer, self).__init__()

        if  player :

            self.addPlayer(player, rating)

    def addPlayer(self, player, rating) :

        self.setRating(player, rating)
        return self

    def getPlayer(self) :
        return self.getAllPlayers()[0]
    
    def getRating(self) :
        return self.getAllRatings()[0]

    def setNewRating(self, rating) :

        return self._playerToRating.setValue(self.getAllPlayers()[0], rating)