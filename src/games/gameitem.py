#-------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------





from PyQt4 import QtCore, QtGui
from fa import maps
import util
import os
from games.moditem import mod_invisible, mods

from trueSkill.Team import *
from trueSkill.Teams import *
from trueSkill.TrueSkill.FactorGraphTrueSkillCalculator import * 
from trueSkill.Rating import *

import client
import copy

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
    
    
    FORMATTER_FAF       = unicode(util.readfile("games/formatters/faf.qthtml"))
    FORMATTER_MOD       = unicode(util.readfile("games/formatters/mod.qthtml"))
    FORMATTER_TOOL      = unicode(util.readfile("games/formatters/tool.qthtml"))
    
    def __init__(self, uid, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.uid            = uid
        self.mapname        = None
        self.mapdisplayname = None
        self.client         = None
        self.title          = None
        self.host           = None
        self.teams          = None
        self.access         = None
        self.mod            = None
        self.mods           = None
        self.moddisplayname = None
        self.state          = None
        self.nTeams         = 0
        self.options        = []
        self.players        = []
        
        self.setHidden(True)

        
    def url(self, player = None):
        if not player:
            player = self.host
            
        
        if self.state == "playing":
            url = QtCore.QUrl()
            url.setScheme("faflive")
            url.setHost("lobby.faforever.com")
            url.setPath(str(self.uid) + "/" + player + ".SCFAreplay")
            url.addQueryItem("map", self.mapname)
            url.addQueryItem("mod", self.mod)
            return url
        elif self.state == "open":
            url = QtCore.QUrl()
            url.setScheme("fafgame")
            url.setHost("lobby.faforever.com")
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

        foo = message
        message = copy.deepcopy(foo)
        
        self.client  = client

        self.title      = message['title']
        self.host       = message['host']
        self.teams      = dict.copy(message['teams'])
        self.access     = message.get('access', 'public')
        self.mod        = message['featured_mod']
        self.modVersion = message.get('featured_mod_versions', [])
        self.mods       = message.get('sim_mods',{})
        self.options    = message.get('options', [])
        self.numplayers = message.get('num_players', 0) 
        self.slots      = message.get('max_players',12)
        
        oldstate = self.state
        self.state  = message['state']
      

        # Assemble a players & teams lists
        self.teamlist = []
        self.observerlist = []
        self.realPlayers = []
        self.teamsTrueskill = []
        self.gamequality = 0
        self.invalidTS = False
        self.nTeams = 0

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
            
        self.players = []
        for team in self.teams:
            self.players.extend(self.teams[team])


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
                    self.client.downloader.downloadMap(self.mapname, self)
                    icon = util.icon("games/unknown_map.png")
                             
            self.setIcon(icon)
        

        # Used to differentiate between newly added / removed and previously present players            
        oldplayers = set(self.players)
        
       
        self.playerIncluded = False
        
        
        if self.state == "open" :
            if "1" in self.teams and "2" in self.teams and self.client.login != None and self.client.login not in self.teams["1"] and self.client.login not in self.teams["2"] :
                if len(self.teams["1"]) < len(self.teams["2"]) :
                    self.teams["1"].append(self.client.login)
                    self.playerIncluded = True

                elif len(self.teams["1"]) > len(self.teams["2"]) :
                    self.teams["2"].append(self.client.login)
                    self.playerIncluded = True

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
                                if self.client.isFoe(player) :
                                    self.hasFoe = True
                                mean = self.client.players[player]["rating_mean"]
                                dev = self.client.players[player]["rating_deviation"]
                                curTeam.addPlayer(player, Rating(mean, dev))
                            else :
                                self.invalidTS = True
                                

                        self.teamsTrueskill.append(curTeam)
                    
                # computing game quality :
                if len(self.teamsTrueskill) > 1 and self.invalidTS == False :
                    self.nTeams = 0
                    for t in self.teams :
                        if int(t) != -1 :
                            self.nTeams += 1

                    realPlayers = len(self.realPlayers)

                    if realPlayers % self.nTeams == 0 :

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


        if len(self.players) == 1:
            playerstring = "player"
        else:
            playerstring = "players"
        
        
        self.numplayers = len(self.players)
        
        self.playerIncludedTxt = ""
        if self.playerIncluded :
            self.playerIncludedTxt = "(with you)"
            
        color = client.getUserColor(self.host)
        
        for player in self.players :
            if self.client.isFoe(player) :
                color = client.getUserColor(player)

        self.editTooltip()
        
        

        if self.mod == "faf" and not self.mods:
            self.setText(self.FORMATTER_FAF.format(color=color, mapslots = self.slots, mapdisplayname=self.mapdisplayname, title=self.title, host=self.host, players=self.numplayers, playerstring=playerstring, gamequality = strQuality, playerincluded = self.playerIncludedTxt))
        else:
            if not self.mods:
                modstr = self.mod
            else:
                if self.mod == 'faf': modstr = ", ".join(self.mods.values())
                else: modstr = self.mod + " & " + ", ".join(self.mods.values())
                if len(modstr) > 20: modstr = modstr[:15] + "..."
            self.setText(self.FORMATTER_MOD.format(color=color, mapslots = self.slots, mapdisplayname=self.mapdisplayname, title=self.title, host=self.host, players=self.numplayers, playerstring=playerstring, gamequality = strQuality, playerincluded = self.playerIncludedTxt, mod=modstr))
        
        if self.uid == 0:
            return
                
        #Spawn announcers: IF we had a gamestate change, show replay and hosting announcements 
        if (oldstate != self.state):            
            if (self.state == "playing"):
                QtCore.QTimer.singleShot(5*60000, self.announceReplay) #The delay is there because we have a 5 minutes delay in the livereplay server
            elif (self.state == "open"):
                QtCore.QTimer.singleShot(35000, self.announceHosting)   #The delay is there because we currently the host needs time to choose a map

        # Update player URLs
        for player in self.players:
            client.urls[player] = self.url(player)

        # Determine which players are affected by this game's state change            
        newplayers = set(self.players)            
        affectedplayers = oldplayers | newplayers
        client.usersUpdated.emit(list(affectedplayers))
        
        
    def editTooltip(self):
        
        observerlist    = []
        teamlist        = []

        teams = ""

        i = 0
        for team in self.teams:
            
            if team != "-1" :
                i = i + 1
                teamtxt = "<table>"

                    
                teamDisplay    = []
                for player in self.teams[team] :
                    displayPlayer = ""
                    if player in self.client.players :
                        
                        playerStr = player
                        
                        if player == self.client.login :
                            playerStr = ("<b><i>%s</b></i>" % player)
                            
                        dev     = self.client.players[player]["rating_deviation"]
                        if dev < 200 :
                            playerStr += " ("+str(self.client.getUserRanking(player))+")"

                        if i == 1 :
                            displayPlayer = ("<td align = 'left' valign='center' width = '150'>%s</td>" % playerStr)
                        elif i == self.nTeams :
                            displayPlayer = ("<td align = 'right' valign='center' width = '150'>%s</td>" % playerStr)
                        else :
                            displayPlayer = ("<td align = 'center' valign='center' width = '150'>%s</td>" % playerStr)
                        
                        
                        country = os.path.join(util.COMMON_DIR, "chat/countries/%s.png" % self.client.players[player]["country"].lower())
                        
                        if i == self.nTeams : 
                            displayPlayer += '<td width="16"><img src = "'+country+'" width="16" height="16"></td>'
                        else :
                            displayPlayer = '<td width="16"><img src = "'+country+'" width="16" height="16"></td>' + displayPlayer
                            
                    else :
                        if i == 1 :
                            displayPlayer = ("<td align = 'left' valign='center' width = '150'>%s</td>" % player)
                        elif i == self.nTeams :
                            displayPlayer = ("<td align = 'right' valign='center' width = '150'>%s</td>" % player)
                        else :
                            displayPlayer = ("<td align = 'center' valign='center' width = '150'>%s</td>" % player)
                        

                        
                    display = ("<tr>%s</tr>" % displayPlayer)
                    teamDisplay.append(display)
                        
                members = "".join(teamDisplay)
                
                teamlist.append("<td>" +teamtxt + members + "</table></td>")
                
                    
                
            else :
                observerlist.append(",".join(self.teams[team]))

        teams += "<td valign='center' height='100%'><font valign='center' color='black' size='+5'>VS</font></td>".join(teamlist)

        self.numplayers = self.numplayers - len(observerlist)

        observers = ""
        if len(observerlist) != 0 :
            observers = "Observers : "
            observers += ",".join(observerlist)        

        mods = "" 
        if len(self.modoptions)!= 0 and len(self.modoptions) == len(self.options):
            mods  += "<br/>Options :<br/>"
   
            for i in range(len(self.modoptions)) :
                mods += self.modoptions[i]
                if self.options[i] == True :                  
                    mods += ": On<br/>"
                else :
                    mods += ": Off<br/>"

        if self.mods: mods += "<br/><br/>With " + "<br/>".join(self.mods.values())

        self.setToolTip(self.FORMATTER_TOOL.format(teams = teams, observers=observers, mods = mods)) 

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
            bestTeams[self.assignToTeam(i)].append(key)
            i = i + 1

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

        # Sort Games
        # 0: By Player Count
        # 1: By Game Quality
        # 2: By avg. Player Rating
        try:
            sortBy = self.listWidget().sortBy
        except AttributeError:
            sortBy = 99
        if (sortBy == 0):
            return len(self.players) > len(other.players)
        elif (sortBy == 1):
            return self.gamequality > other.gamequality
        elif (sortBy == 2):
            return self.average_rating > other.average_rating
        else:
            # Default: by UID.
            return self.uid < other.uid

    @property
    def average_rating(self):
        rating = 0
        for player in self.players :
            try:
                mean = self.client.players[player]["rating_mean"]
                dev = self.client.players[player]["rating_deviation"]
                rating += mean - 3 * dev
            except KeyError:
                pass
        return rating
