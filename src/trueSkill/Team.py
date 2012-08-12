from Rating import *
from Player import *
from RatingContainer import *

class Team(RatingContainer) :
    def __init__(self, player = None, rating = None):
    
        super(Team, self).__init__()

        if  player :

            self.addPlayer(player, rating)

    def addPlayer(self, player, rating) :

        self.setRating(player, rating)
        return self
    

    def addTeam(self, team):
        

        for player in team.getAllPlayers() :
 
            self.addPlayer(player, team.getRating(player))
            