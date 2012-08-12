from Numerics.Range import *


class PlayersRange(Range) :
    def __init__(self, min, max):
        super(PlayersRange, self).__init__(min, max)
    
    
    def create(min, max) :

        return  PlayersRange(min, max);
