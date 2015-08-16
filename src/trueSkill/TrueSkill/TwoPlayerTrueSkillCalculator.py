



from SkillCalculator import *
from Numerics.BasicMath import *
from Numerics.Range import *
from PlayersRange import *
from TeamsRange import *
from Guard import *
from math import sqrt
from RankSorter import *
from RatingContainer import *
from PairwiseComparison import *
from DrawMargin import *
from TruncatedGaussianCorrectionFunctions import *

# * Calculates the new ratings for only two players.
# * 
# * When you only have two players, a lot of the math simplifies. The main purpose of this class
# * is to show the bare minimum of what a TrueSkill implementation should have.
# */

class TwoPlayerTrueSkillCalculator (SkillCalculator) :

    def __init__(self):
        super(TwoPlayerTrueSkillCalculator, self).__init__(SkillCalculatorSupportedOptions.NONE, TeamsRange.exactly(2), PlayersRange.exactly(1))
        


    def calculateNewRatings(self, gameInfo, teams, teamRanks) :
        # Basic argument checking
        Guard.argumentNotNull(gameInfo, "gameInfo")
        self.validateTeamCountAndPlayersCountPerTeam(teams)

        #Make sure things are in order
        RankSorter.sort(teams, teamRanks)
        
        #Since we verified that each team has one player, we know the player is the first one
        winningTeamPlayers = teams[0].getAllPlayers()
        winner = winningTeamPlayers[0]
        winnerPreviousRating = teams[0].getRating(winner)      
       
        losingTeamPlayers = teams[1].getAllPlayers()
        loser = losingTeamPlayers[0]
        loserPreviousRating = teams[1].getRating(loser)

        wasDraw = False
        if teamRanks[0] == teamRanks[1] :
            wasDraw = True


        results = RatingContainer()
        
        resultWin = ''
        resultLost = ''
        if wasDraw :
            resultWin = PairwiseComparison.DRAW
            resultLost = PairwiseComparison.DRAW
        else :
            resultWin = PairwiseComparison.WIN
            resultLost = PairwiseComparison.LOSE


        
        results.setRating(winner, self.calculateNewRating(gameInfo,
                                                              winnerPreviousRating,
                                                              loserPreviousRating,
                                                            resultWin))

        results.setRating(loser, self.calculateNewRating(gameInfo,
                                                             loserPreviousRating,
                                                             winnerPreviousRating,
                                                             resultLost))

        #// And we're done!

        return results


    def calculateNewRating(self, gameInfo, selfRating, opponentRating, comparison) :

        drawMargin = DrawMargin.getDrawMarginFromDrawProbability(gameInfo.getDrawProbability(),
                                                                   gameInfo.getBeta())

        c =sqrt(
                square(selfRating.getStandardDeviation())
                +
                square(opponentRating.getStandardDeviation())
                +
                2*square(gameInfo.getBeta()))

        winningMean = selfRating.getMean()
        losingMean = opponentRating.getMean()


        if comparison == PairwiseComparison.LOSE :

                winningMean = opponentRating.getMean()
                losingMean = selfRating.getMean()


        meanDelta = winningMean - losingMean

        if (comparison != PairwiseComparison.DRAW) :

            # non-draw case
            v = TruncatedGaussianCorrectionFunctions.vExceedsMarginScaled(meanDelta, drawMargin, c)
            w = TruncatedGaussianCorrectionFunctions.wExceedsMarginScaled(meanDelta, drawMargin, c)
            rankMultiplier = comparison

        else :

            v = TruncatedGaussianCorrectionFunctions.vWithinMarginScaled(meanDelta, drawMargin, c)
            w = TruncatedGaussianCorrectionFunctions.wWithinMarginScaled(meanDelta, drawMargin, c)
            rankMultiplier = 1


        meanMultiplier = (square(selfRating.getStandardDeviation()) + square(gameInfo.getDynamicsFactor()))/c;

        varianceWithDynamics = square(selfRating.getStandardDeviation()) + square(gameInfo.getDynamicsFactor())
        stdDevMultiplier = varianceWithDynamics/square(c)

        newMean = selfRating.getMean() + (rankMultiplier*meanMultiplier*v)
        newStdDev = sqrt(varianceWithDynamics*(1 - w*stdDevMultiplier))

        return  Rating(newMean, newStdDev)

#    /**
#     * {@inheritdoc }
#     */
    def calculateMatchQuality(self, gameInfo, teams) :

        Guard.argumentNotNull(gameInfo, "gameInfo")
        self.validateTeamCountAndPlayersCountPerTeam(teams)

        team1 = teams[0]

        team2 = teams[1]

        team1Ratings = team1.getAllRatings()
        team2Ratings = team2.getAllRatings()

        player1Rating = team1Ratings[0]
        player2Rating = team2Ratings[0]
        
        #// We just use equation 4.1 found on page 8 of the TrueSkill 2006 paper:
        betaSquared = square(gameInfo.getBeta())
        player1SigmaSquared = square(player1Rating.getStandardDeviation())
        player2SigmaSquared = square(player2Rating.getStandardDeviation())

        #// This is the square root part of the equation:
        sqrtPart = sqrt((2*betaSquared) / (2*betaSquared + player1SigmaSquared + player2SigmaSquared))

        #// This is the exponent part of the equation:
        expPart = exp(
                (-1*square(player1Rating.getMean() - player2Rating.getMean()))
                /
                (2*(2*betaSquared + player1SigmaSquared + player2SigmaSquared)))

        return sqrtPart*expPart
