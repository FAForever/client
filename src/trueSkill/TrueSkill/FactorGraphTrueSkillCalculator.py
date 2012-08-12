from trueSkill.SkillCalculator import *
from trueSkill.GameInfo import *
from trueSkill.SkillCalculator import *
from trueSkill.Numerics.Matrix import *
from trueSkill.Numerics.BasicMath import *

from trueSkill.PartialPlay import *

from trueSkill.Rating import *
from trueSkill.Guard import *
from trueSkill.RankSorter import *
from trueSkill.TrueSkill.TrueSkillFactorGraph import *
#/**
# * Calculates TrueSkill using a full factor graph.
# */
class FactorGraphTrueSkillCalculator(SkillCalculator) :
    def __init__(self) :
        super(FactorGraphTrueSkillCalculator, self).__init__(SkillCalculatorSupportedOptions.NONE, TeamsRange.atLeast(2), PlayersRange.atLeast(1))
    

    def calculateNewRatings(self, gameInfo,
                                        teams,
                                        teamRanks) :


        Guard.argumentNotNull(gameInfo, "gameInfo")

        self.validateTeamCountAndPlayersCountPerTeam(teams)

        
        teamRanks, teams = RankSorter.sort(teams, teamRanks)      
  
        factorGraph = TrueSkillFactorGraph(gameInfo, teams, teamRanks)

        factorGraph.buildGraph()

        factorGraph.runSchedule()
       
        probabilityOfOutcome = factorGraph.getProbabilityOfRanking()


        return factorGraph.getUpdatedRatings()

    #@staticmethod
    def calculateMatchQuality(self, gameInfo, teams) :

#        // We need to create the A matrix which is the player team assigments.
        teamAssignmentsList = teams



        skillsMatrix = self.getPlayerCovarianceMatrix(teamAssignmentsList)
        
       
        meanVector = self.getPlayerMeansVector(teamAssignmentsList)

        meanVectorTranspose = meanVector.getTranspose()

        playerTeamAssignmentsMatrix = self.createPlayerTeamAssignmentMatrix(teamAssignmentsList, meanVector.getRowCount())
        

        
        playerTeamAssignmentsMatrixTranspose = playerTeamAssignmentsMatrix.getTranspose()


        betaSquared = square(gameInfo.getBeta())

        start = Matrix.multiply(meanVectorTranspose, playerTeamAssignmentsMatrix)
        

        
        aTa = Matrix.multiply(Matrix.scalarMultiply(betaSquared,
                                               playerTeamAssignmentsMatrixTranspose),
                                                playerTeamAssignmentsMatrix)
        aTSA = Matrix.multiply(
                    Matrix.multiply(playerTeamAssignmentsMatrixTranspose, skillsMatrix),
                    playerTeamAssignmentsMatrix)



        middle = Matrix.add(aTa, aTSA)


        middleInverse = middle.getInverse()

        end = Matrix.multiply(playerTeamAssignmentsMatrixTranspose, meanVector)

        expPartMatrix = Matrix.scalarMultiply(-0.5, (Matrix.multiply(Matrix.multiply(start, middleInverse), end)))
        expPart = expPartMatrix.getDeterminant()

        sqrtPartNumerator = aTa.getDeterminant()
        sqrtPartDenominator = middle.getDeterminant()
        sqrtPart = sqrtPartNumerator / sqrtPartDenominator

        result = exp(expPart) * sqrt(sqrtPart)

        return result


    def getRatingPlayerMeansVector(self, rating):
        return rating.getMean()

    #@staticmethod
    def getPlayerMeansVector(self, teamAssignmentsList) :

        
        #// A simple vector of all the player means.
        return Vector(self.getPlayerRatingValues(teamAssignmentsList,self.getRatingPlayerMeansVector))

    
    def getRatingStandardDeviation(self, rating) :
         return square(rating.getStandardDeviation())


    #@staticmethod 
    def getPlayerCovarianceMatrix(self, teamAssignmentsList) :

        # This is a square matrix whose diagonal values represent the variance (square of standard deviation) of all
        # players.
        diagMatrix = DiagonalMatrix(self.getPlayerRatingValues(teamAssignmentsList, self.getRatingStandardDeviation))

        return diagMatrix

#
#    // Helper function that gets a list of values for all player ratings
    @staticmethod
    def getPlayerRatingValues(teamAssignmentsList, playerRatingFunction) :
        playerRatingValues = []
        for currentTeam in teamAssignmentsList : 
            for currentRating in currentTeam.getAllRatings() :
                playerRatingValues.append(playerRatingFunction(currentRating))

        return playerRatingValues

#
    @staticmethod
    def createPlayerTeamAssignmentMatrix(teamAssignmentsList, totalPlayers) :
        
#        // The team assignment matrix is often referred to as the "A" matrix. It's a matrix whose rows represent the players
#        // and the columns represent teams. At Matrix[row, column] represents that player[row] is on team[col]
#        // Positive values represent an assignment and a negative value means that we subtract the value of the next
#        // team since we're dealing with pairs. This means that this matrix always has teams - 1 columns.
#        // The only other tricky thing is that values represent the play percentage.
#
#        // For example, consider a 3 team game where team1 is just player1, team 2 is player 2 and player 3, and
#        // team3 is just player 4. Furthermore, player 2 and player 3 on team 2 played 25% and 75% of the time
#        // (e.g. partial play), the A matrix would be:
#
#        // A = this 4x2 matrix:
#        // |  1.00  0.00 |
#        // | -0.25  0.25 |
#        // | -0.75  0.75 |
#        // |  0.00 -1.00 |
        playerAssignments = []
        totalPreviousPlayers = 0

        teamAssignmentsListCount = len(teamAssignmentsList)
        
        currentColumn = 0
        
        for i in range(teamAssignmentsListCount-1) :

            currentTeam = teamAssignmentsList[i]

 
#            // Need to add in 0's for all the previous players, since they're not
#            // on this team
            result = [] 
            if totalPreviousPlayers > 0 :
                result = [0] * totalPreviousPlayers



            playerAssignments.insert(currentColumn, result)
            #playerAssignments[currentColumn] = result

            for currentPlayer in currentTeam.getAllPlayers() : 

                playerAssignments[currentColumn].append(PartialPlay.getPartialPlayPercentage(currentPlayer))
#                // indicates the player is on the team
                totalPreviousPlayers = totalPreviousPlayers + 1


            rowsRemaining = totalPlayers - totalPreviousPlayers
            nextTeam = teamAssignmentsList[i + 1]
            
            for nextTeamPlayer in nextTeam.getAllPlayers() : 

#                // Add a -1 * playing time to represent the difference
                playerAssignments[currentColumn].append( -1 * PartialPlay.getPartialPlayPercentage(nextTeamPlayer))
                rowsRemaining = rowsRemaining - 1

            for ixAdditionalRow in range(rowsRemaining) :
#                // Pad with zeros
                playerAssignments[currentColumn].append(0)

            currentColumn = currentColumn + 1


        playerTeamAssignmentsMatrix = Matrix.fromColumnValues(totalPlayers, teamAssignmentsListCount - 1, playerAssignments)

        return playerTeamAssignmentsMatrix
 