from PyQt4 import QtCore, QtGui
from fa import maps
import util
from games.moditem import mod_invisible, mods

from trueSkill.Team import *
from trueSkill.Teams import *
from trueSkill.TrueSkill.FactorGraphTrueSkillCalculator import * 
from trueSkill.Rating import *

import client


class GameItemDelegate(QtGui.QStyledItemDelegate):
    
    def __init__(self, *args, **kwargs):
        QtGui.QStyledItemDelegate.__init__(self, *args, **kwargs)
        
    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
                
        painter.save()
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        
        icon = QtGui.QIcon(option.icon)
        iconsize = icon.actualSize(option.rect.size())
        
        #clear icon and text before letting the control draw itself because we're rendering these parts ourselves
        option.icon = QtGui.QIcon()        
        option.text = ""  
        option.widget.style().drawControl(QtGui.QStyle.CE_ItemViewItem, option, painter, option.widget)
        
        #Shadow
        painter.fillRect(option.rect.left()+8-1, option.rect.top()+8-1, iconsize.width(), iconsize.height(), QtGui.QColor("#202020"))

        #Icon
        icon.paint(painter, option.rect.adjusted(5-2, -2, 0, 0), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        
        #Frame around the icon
        pen = QtGui.QPen()
        pen.setWidth(1);
        pen.setBrush(QtGui.QColor("#303030"));  #FIXME: This needs to come from theme.
        pen.setCapStyle(QtCore.Qt.RoundCap);
        painter.setPen(pen)
        painter.drawRect(option.rect.left()+5-2, option.rect.top()+5-2, iconsize.width(), iconsize.height())

        #Description
        painter.translate(option.rect.left() + iconsize.width() + 10, option.rect.top()+10)
        clip = QtCore.QRectF(0, 0, option.rect.width()-iconsize.width() - 10 - 5, option.rect.height())
        html.drawContents(painter, clip)
  
        painter.restore()
        

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(GameItem.TEXTWIDTH)
        return QtCore.QSize(GameItem.ICONSIZE + GameItem.TEXTWIDTH + GameItem.PADDING, GameItem.ICONSIZE)  





class GameItem(QtGui.QListWidgetItem):
    TEXTWIDTH = 230
    ICONSIZE = 110
    PADDING = 10
    
    WIDTH = ICONSIZE + TEXTWIDTH
    #DATA_PLAYERS = 32
    
    
    FORMATTER_FAF = unicode(util.readfile("games/formatters/faf.qthtml"))
    FORMATTER_MOD = unicode(util.readfile("games/formatters/mod.qthtml"))
    
    def __init__(self, uid, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.uid = uid
        self.mapname = None
        self.mapdisplayname = None      
        self.client = None
        self.title  = None
        self.host   = None
        self.teams  = None
        self.access = None
        self.mod    = None
        self.moddisplayname  = None
        self.state  = None
        self.options = []
        self.players = []
        
        self.setHidden(True)

        
    def url(self, player = None):
        if not player:
            player = self.host
            
        
        if self.state == "playing":
            url = QtCore.QUrl()
            url.setScheme("faflive")
            url.setHost("faforever.com")
            url.setPath(str(self.uid) + "/" + player + ".SCFAreplay")
            url.addQueryItem("map", self.mapname)
            url.addQueryItem("mod", self.mod)
            return url
        elif self.state == "open":
            url = QtCore.QUrl()
            url.setScheme("fafgame")
            url.setHost("faforever.com")
            url.setPath(self.host)
            url.addQueryItem("map", self.mapname)
            url.addQueryItem("mod", self.mod)
            url.addQueryItem("uid", str(self.uid))
            return url
        return None 
        
        
    @QtCore.pyqtSlot()
    def announceReplay(self):
        if not self.client.isFriend(self.host):
            return

        if not self.state == "playing":
            return
                
        # User doesnt want to see this in chat   
        if not self.client.livereplays:
            return

        url = self.url()
                      
        if self.mod == "faf":
            self.client.forwardLocalBroadcast(self.host, 'is playing live in <a style="color:' + self.client.getColor("url") + '" href="' + url.toString() + '">' + self.title + '</a> (on "' + self.mapdisplayname + '")')
        else:
            self.client.forwardLocalBroadcast(self.host, 'is playing ' + self.moddisplayname + ' in <a style="color:' + self.client.getColor("url") + '" href="' + url.toString() + '">' + self.title + '</a> (on "' + self.mapdisplayname + '")')
        
    
    @QtCore.pyqtSlot()
    def announceHosting(self):
        if not self.client.isFriend(self.host) or self.isHidden() or self.private:
            return

        if not self.state == "open":
            return
                
        url = self.url()
                
        # Join url for single sword
        client.instance.urls[self.host] = url
        
        # No visible message if not requested   
        if not self.client.opengames:
            return
                         
        if self.mod == "faf":
            self.client.forwardLocalBroadcast(self.host, 'is hosting <a style="color:' + self.client.getColor("url") + '" href="' + url.toString() + '">' + self.title + '</a> (on "' + self.mapdisplayname + '")')
        else:
            self.client.forwardLocalBroadcast(self.host, 'is hosting ' + self.moddisplayname + ' <a style="color:' + self.client.getColor("url") + '" href="' + url.toString() + '">' + self.title + '</a> (on "' + self.mapdisplayname + '")')
            
    
    
    def update(self, message, client):
        '''
        Updates this item from the message dictionary supplied
        '''
        
        self.client  = client

        self.title      = message['title']
        self.host       = message['host']
        self.teams      = message['teams']
        self.access     = message.get('access', 'public')
        self.mod        = message['featured_mod']
        self.options    = message.get('options', [])
        self.numplayers = message.get('num_players', 0) 
        self.slots      = message.get('max_players',12)
        
        oldstate = self.state
        self.state  = message['state']
 

        #HACK: Visibility field not supported yet.
        self.private = self.title.lower().find("private") != -1        
        self.setHidden((self.state != 'open') or (self.mod in mod_invisible))        


        # Clear the status for all involved players (url may change, or players may have left, or game closed)        
        for player in self.players:
            if player in client.urls:
                del client.urls[player]


        # Just jump out if we've left the game, but tell the client that all players need their states updated
        if self.state == "closed":
            client.usersUpdated.emit(self.players)
            return
            

        # Map preview code
        if self.mapname != message['mapname']:
            self.mapname = message['mapname']
            self.mapdisplayname = maps.getDisplayName(self.mapname)
            refresh_icon = True
        else:
            refresh_icon = False
                    
        #Resolve pretty display name
        self.moddisplayname = self.mod
        self.modoptions = []
        
        if self.mod in mods :
            self.moddisplayname = mods[self.mod].name 
            self.modoptions = mods[self.mod].options
        

        #Checking if the mod has options

        #Alternate icon: If private game, use game_locked icon. Otherwise, use preview icon from map library.
        if refresh_icon:
            if self.access == "password" or self.private:
                icon = util.icon("games/private_game.png")
            else:            
                icon = maps.preview(self.mapname)
                if not icon:
                    icon = util.icon("games/unknown_map.png")
                                        
            self.setIcon(icon)
        

        # Used to differentiate between newly added / removed and previously present players            
        oldplayers = set(self.players)
        
        # Assemble a players & teams lists       
        self.teamlist = []
        self.observerlist = []
        self.players = []
        self.realPlayers = []
        self.teamsTrueskill = []
        self.gamequality = 0
        self.invalidTS = False
        
        self.playerIncluded = False
        
        tooltipstring = ""
        if self.state == "open" :
            if "1" in self.teams and "2" in self.teams and self.client.login != None :

                if len(self.teams["1"]) < len(self.teams["2"]) :
                    #self.teams["1"].append(self.client.login)
                    tooltipstring = "You should be in team 1.<br><br>"
                    self.playerIncluded = True

                elif len(self.teams["1"]) > len(self.teams["2"]) :
                    #self.teams["2"].append(self.client.login)
                    tooltipstring = "You should be in team 2.<br><br>"
                    self.playerIncluded = True
        
        
        for team in self.teams:
            self.players.extend(self.teams[team])
            if team != "-1" :
                self.teamlist.append(", ".join(self.teams[team]))
            else :
                self.observerlist.append(", ".join(self.teams[team]))

        if self.state == "open" and  "1" in self.teams and "2" in self.teams :
            for team in self.teams:
                if team != "-1" :
                    self.realPlayers.extend(self.teams[team])
                    if team == 0 :
                        for player in self.teams[team] :
                            curTeam = Team()
                            if player in self.client.players :
                                mean = self.client.players[player]["rating_mean"]
                                dev = self.client.players[player]["rating_deviation"]
                                curTeam.addPlayer(player, Rating(mean, dev))
                            else :
                                self.invalidTS = True
                            self.teamsTrueskill.append(curTeam)
                    else :
                        curTeam = Team()

                        if team == "1" and (len(self.teams["1"]) < len(self.teams["2"])) and self.playerIncluded == True :
                            if self.client.login in self.client.players :
                                curTeam.addPlayer(self.client.login, Rating(self.client.players[self.client.login]["rating_mean"], self.client.players[self.client.login]["rating_deviation"]))
                        
                        if team == "2" and (len(self.teams["1"]) > len(self.teams["2"])) and self.playerIncluded == True :
                            if self.client.login in self.client.players :
                                curTeam.addPlayer(self.client.login, Rating(self.client.players[self.client.login]["rating_mean"], self.client.players[self.client.login]["rating_deviation"]))

                        for player in self.teams[team] :          
                            if player in self.client.players :
                                mean = self.client.players[player]["rating_mean"]
                                dev = self.client.players[player]["rating_deviation"]
                                curTeam.addPlayer(player, Rating(mean, dev))
                            else :
                                self.invalidTS = True
                                

                        self.teamsTrueskill.append(curTeam)
                    
                # computing game quality :
                if len(self.teamsTrueskill) > 1 and self.invalidTS == False :
                    nTeams = 0
                    for t in  self.teamlist :
                        if t != -1 :
                            nTeams += 1
                            
                    realPlayers = len(self.realPlayers) 
                    if self.playerIncluded :
                        realPlayers = realPlayers + 1
                    if realPlayers % nTeams == 0 :
                        gameInfo = GameInfo()
                        calculator = FactorGraphTrueSkillCalculator()
                        gamequality = calculator.calculateMatchQuality(gameInfo, self.teamsTrueskill)
                        if gamequality < 1 :
                            self.gamequality = round((gamequality * 100), 2)
                   
        strQuality = ""
        
        if self.gamequality == 0 :
            strQuality = "? %"
        else :
            strQuality = str(self.gamequality)+" %"

        #bestMatchup = self.getBestMatchup()

        
        tooltipstring += " vs.<br/>".join(self.teamlist)
        if len(self.observerlist) != 0 :
            tooltipstring += "<br/>Observers :<br/>".join(self.observerlist)
        
        #tooltipstring += "<br/><br/>Best team composition : <br/>" + bestMatchup
        
        if len(self.modoptions)!= 0 and len(self.modoptions) == len(self.options):
            tooltipstring += "<br/><br/>Options :<br/>"
            
            for i in range(len(self.modoptions)) :
                tooltipstring += self.modoptions[i]
                if self.options[i] == True :                  
                    tooltipstring += ": On<br/>"
                else :
                    tooltipstring += ": Off<br/>"
 

        self.setToolTip(tooltipstring)
                  
        if len(self.players) == 1:
            playerstring = "player"
        else:
            playerstring = "players"
        
        if self.numplayers == 0 :
            self.numplayers = len(self.players)
        
        self.playerIncludedTxt = ""
        if self.playerIncluded :
            self.playerIncludedTxt = "(with you)"
            
        color = client.getUserColor(self.host)              
        if self.mod == "faf":
            self.setText(self.FORMATTER_FAF.format(color=color, mapslots = self.slots, mapdisplayname=self.mapdisplayname, title=self.title, host=self.host, players=self.numplayers, playerstring=playerstring, gamequality = strQuality, playerincluded = self.playerIncludedTxt))
        else:
            self.setText(self.FORMATTER_MOD.format(color=color, mapslots = self.slots, mapdisplayname=self.mapdisplayname, title=self.title, host=self.host, players=self.numplayers, playerstring=playerstring, gamequality = strQuality, playerincluded = self.playerIncludedTxt, mod=self.mod))
        
                
        #Spawn announcers: IF we had a gamestate change, show replay and hosting announcements 
        if (oldstate != self.state):            
            if (self.state == "playing"):
                QtCore.QTimer.singleShot(60000, self.announceReplay) #The delay is there because we have a 60 delay in the livereplay server
            elif (self.state == "open"):
                QtCore.QTimer.singleShot(35000, self.announceHosting)   #The delay is there because we currently the host needs time to choose a map

        # Update player URLs
        for player in self.players:
            client.urls[player] = self.url(player)

        # Determine which players are affected by this game's state change            
        newplayers = set(self.players)            
        affectedplayers = oldplayers | newplayers
        client.usersUpdated.emit(list(affectedplayers))
        

    def permutations(self, items):
        """Yields all permutations of the items."""
        if items == []:
            yield []
        else:
            for i in range(len(items)):
                for j in self.permutations(items[:i] + items[i+1:]):
                    yield [items[i]] + j


    

    def assignToTeam(self, num) :
        ''' return the team of the player based on his place/rating '''
        even = 0
        while num > 0 :
            rest = num % 2
            if rest == 1 :
                even = even + 1
            num=(num-rest)/2
        
        if even % 2 == 0 :
            return 1
        else :
            return 2

    def getBestMatchup(self):
        

        
        if not self.state == "open":
            return "game in play"
        
        nTeams = 0
        for t in  self.teamlist :
            if t != -1 :
                nTeams += 1
        
        
        if nTeams != 2 or len(self.players) <= 2 :
            return "No teams formed yet"
        
       
        if len(self.players) % nTeams :
            return "Missing players for this number of teams (%i)" % (int(nTeams))
        if (len(self.players) / nTeams) == 1 :
            
            return "Only one player per team" 

         #platoon = len(self.players) / nTeams
            
        playerlist =  {}  
        for player in self.players :
            mean = self.client.players[player]["rating_mean"]
            dev = self.client.players[player]["rating_deviation"]
            rating = mean - 3 * dev
            playerlist[player] = rating
        
        i = 0
        
        bestTeams = {}
        bestTeams[1] = []
        bestTeams[2] = []
        
        for key, value in sorted(playerlist.iteritems(), key=lambda (k,v): (v,k), reverse=True):
            print "%s: %s in team %i" % (key, value, self.assignToTeam(i))
            bestTeams[self.assignToTeam(i)].append(key)
            i = i + 1
        print "---"

        msg = ""
#        i = 0
#        for teams in winningTeam :
#            
        msg += ", ".join(bestTeams[1])
#            i = i + 1
#            if i != len(winningTeam) :
        msg += "<br/>Vs<br/>"
        msg += ", ".join(bestTeams[2])
        
        teamsTrueskill = []
        invalidTS = False
        
        for player in bestTeams[1] :
            curTeam = Team()
            if player in self.client.players :
                mean = self.client.players[player]["rating_mean"]
                dev = self.client.players[player]["rating_deviation"]
                curTeam.addPlayer(player, Rating(mean, dev))
            else :
                self.invalidTS = True
            teamsTrueskill.append(curTeam)

        for player in bestTeams[2] :
            curTeam = Team()
            if player in self.client.players :
                mean = self.client.players[player]["rating_mean"]
                dev = self.client.players[player]["rating_deviation"]
                curTeam.addPlayer(player, Rating(mean, dev))
            else :
                self.invalidTS = True
            teamsTrueskill.append(curTeam)
    
        # computing game quality :
        if  invalidTS == False :

            gameInfo = GameInfo()
            calculator = FactorGraphTrueSkillCalculator()
            gamequality = calculator.calculateMatchQuality(gameInfo, teamsTrueskill)
            if gamequality < 1 :
                gamequality = round((gamequality * 100), 2)

        
        
                msg = msg + "<br/>Game Quality will be : " + str(gamequality) + '%' 
        return msg

    def __ge__(self, other):
        ''' Comparison operator used for item list sorting '''        
        return not self.__lt__(other)
    
    
    def __lt__(self, other):
        ''' Comparison operator used for item list sorting '''        
        if not self.client: return True # If not initialized...
        if not other.client: return False;
        
        # Friend games are on top
        if self.client.isFriend(self.host) and not self.client.isFriend(other.host): return True
        if not self.client.isFriend(self.host) and self.client.isFriend(other.host): return False
        
        # Private games are on bottom
        if (not self.private and other.private): return True;
        if (self.private and not other.private): return False;
        
        # Default: Alphabetical
        return self.title.lower() < other.title.lower()
    


