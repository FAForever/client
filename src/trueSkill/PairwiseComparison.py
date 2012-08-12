class PairwiseComparison :

    WIN = 1
    DRAW = 0
    LOSE = -1

    def getRankFromComparison(comparison) :

        if comparaison == WIN :
                return (1,2)
        elif  comparaison == LOSE :
                return (2,1)
        else :
                return (1,1)
