from TrueSkill.TwoPlayerTrueSkillCalculator import *
from Player import *
from Team import *
from Teams import *
        
import time
   
from TrueSkill.FactorGraphTrueSkillCalculator import *  


time1 = time.time()

gameInfo = GameInfo()

calculator = FactorGraphTrueSkillCalculator()
#

player1 = Player(1)
player2 = Player(2)
#player3 = Player(3)
#player4 = Player(4)
#player5 = Player(5)
#player6 = Player(6)

test1 = Team()
test2 = Team()
#test3 = Team()
#test4 = Team()
#test5 = Team()
#test6 = Team()
test1.addPlayer(player1, Rating(1500.0,500.0))
test2.addPlayer(player2, Rating(1500.0,500.0))
#test3.addPlayer(player3, Rating(27.0,8.0))
#test4.addPlayer(player4, Rating(40.0,5.0))
#test5.addPlayer(player5, Rating(32.0,2.0))
#test6.addPlayer(player6, Rating(24.0,4.0))

print "player 1 : "
print test1.getRating(player1)
print "player 2 : "
print test2.getRating(player2)
#print "player 3 : "
#print test3.getRating(player3)
#print "player 4 : "
#print test4.getRating(player4)
#print "player 5 : "
#print test5.getRating(player5)
#print "player 6 : "
#print test6.getRating(player6)
players= []
players.append(test1)
players.append(test2)
#players.append(test3)
#players.append(test4)
#players.append(test5)
#players.append(test6)


nTeams = 3

print "configuration : %i teams" % nTeams

if len(players) % nTeams :
    players.append(None)

def permutations(items):
    """Yields all permutations of the items."""
    if items == []:
        yield []
    else:
        for i in range(len(items)):
            for j in permutations(items[:i] + items[i+1:]):
                yield [items[i]] + j
                
                
    
   
    
platoon = len(players) / nTeams
    
matchs = []   
for perm in list(permutations(players)) :
    
        
    match = []
    for j in range(nTeams) :
        
        team = []
        
        for i in range(platoon) :
            index = i+platoon*j
            team.append(perm[index])

#        team.append(perm[i])
        team=sorted(team)


        match.append(team)
    
    matchs.append(match)


a = []

matchQuality = 0
winningTeam = None

for item in matchs:
    if not item[0] in a:
        a.append(item[0])
        
       
        
        Teams = []
        for i in range(nTeams) :
            resultTeam = Team()
            for j in range(len(item[i])) :

                for player in item[i][j].getAllPlayers() : 
                         resultTeam.addPlayer(player, item[i][j].getRating(player))

            Teams.append(resultTeam)
            

        curQual = calculator.calculateMatchQuality(gameInfo, Teams)
        if curQual > matchQuality :
            matchQuality = curQual
            winningTeam = Teams
            

        #print Teams
        #print "match quality iteration :" + str(calculator.calculateMatchQuality(gameInfo, Teams) * 100) + "%"
            
print "\nthe best composition for teams is "


i  = 1
print len(winningTeam)
for teams in winningTeam :
    print 'team %i' %i

    for player in teams.getAllPlayers() :
        
        print "player "  + str(player.getId()) + "(" + str(teams.getRating(player)) + ")"
    i = i + 1


print "Game Quality ; " + str(matchQuality * 100) + '%' 
time2 = time.time()

running = time2 - time1
print "\nexecution time %f seconds" % running