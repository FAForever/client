



from HashMap import *
from Player import *
from Rating import *


class RatingContainer(object):
    def __init__(self):
        self._playerToRating = HashMap()


    def getRating(self, player) :

        rating = self._playerToRating.getValue(player)
        return rating


    def setRating(self, player, rating) :

        return self._playerToRating.setValue(player, rating)

    
    def getAllPlayers(self) :

        allPlayers = self._playerToRating.getAllKeys()
        return allPlayers

    def getAllPlayersNames(self) :

        allPlayers = self._playerToRating.getAllKeys()
        list = []
        for player in allPlayers :
            list.append(player.getId())
        return list

    
    def getAllRatings(self) :

        allRatings = self._playerToRating.getAllValues()
        return allRatings


    def count(self) :
        return self._playerToRating.count()

    def __iter__(self):
        obj = []
        obj.append(self._playerToRating.getAllKeys())
        obj.append(self._playerToRating.getAllValues())

        return iter(obj)

    
#    def next(self):
#        list = []
#        for player in self.getAllPlayers() :
#            list.append(player)
#        for i in range(self.count()) :
#            if i == self.index :
#                return list[i] 
