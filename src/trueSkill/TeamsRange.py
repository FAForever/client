



from Numerics.Range import *


class TeamsRange(Range) :
    def __init__(self, min, max):
        super(TeamsRange, self).__init__(min, max)
    
    
    def create(min, max) :
        return  TeamsRange(min, max);
