from PyQt4 import QtCore, QtGui, Qt
import util, copy

from tourneys import logger
from tourneys.swisstourneyitem import SwissTourneyItem, SwissTourneyItemDelegate
from tourneys.swissbracketitem import SwissBracketItem, SwissBracketItemDelegate, SwissRoundItem, SwissRoundItemDelegate 
from tourneys.tourneytypeitem import TourneyTypeItem
from tourneys.hosttourneywidget import HostTourneyWidget
import fa

FormClass, BaseClass = util.loadUiType("tournaments/tournaments.ui")


class TournamentWidget(QtGui.QWidget):
    '''this class represent the layout of the tab for a tournament'''
    def __init__(self, tourney, parent=None):
        super(TournamentWidget, self).__init__(parent)
        self.tourney = tourney 
        
        self.table = QtGui.QTableWidget()
        self.score = QtGui.QTextEdit()
        self.finalresult = QtGui.QTextEdit()
        
        self.finalresult.setReadOnly(1)
        self.score.setReadOnly(1)
        
        self.score.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.finalresult.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        
        
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.setSpacing(0)
        mainLayout.setContentsMargins(0,0,0,0)
        if tourney.state == "finished" :
            mainLayout.addWidget(self.finalresult)
            

        
        mainLayout.addWidget(self.table)
        mainLayout.addWidget(self.score) 
        

  
        self.setLayout(mainLayout) 

    @QtCore.pyqtSlot(QtGui.QTableWidgetItem)
    def bracketPressed(self, item):
        if QtGui.QApplication.mouseButtons() == QtCore.Qt.RightButton:            
            #Look up the associated bracket object        
            if hasattr(item, "pressed") :
                item.pressed(item)
                


    def compute_median_buchholz(self, scores, rounds):
        
        tbresults = {}
        
        
        for rnd in rounds :
            pairings = rounds[rnd]
            for pair in pairings :
                if not pair in tbresults :
                    tbresults[pair] = []
                
                if  "result"  in pairings[pair] :
                    if "against" in pairings[pair] : 
                        if pairings[pair]["against"] in scores :
                            tbresults[pair].append(scores[pairings[pair]["against"]]["score"])
                            

        for result in tbresults :
            #removing highest and lowest results
            if len(tbresults[result]) > 0 :
                tbresults[result].remove(max(tbresults[result]))
            if len(tbresults[result]) > 0 :    
                tbresults[result].remove(min(tbresults[result]))               
            if len(tbresults[result]) > 0 :
            #then we add all the results
                S = sum(int(v) for v in tbresults[result])
            else :
                S = 0
            
            if result in scores :
                scores[result]["tb"] = S
                
        


    def displayScores(self,  message):
        self.score.clear()
        text  = ("<table border='1px'><tr><th></th><th>Match W-L-T <br> (wins +1.0, ties +0.5)</th><th>Byes<br>(+1.0)</th><th>Tie-break<br>Score</th><th>Score</th></tr>")
        
        infos = message["result"]
        rounds = infos.get("pairings", {})

        results = {}

        
        for rnd in rounds :
            pairings = rounds[rnd]
            for pair in pairings :
            
                if not pair in results :
                    
                    results[pair] = {}
                    results[pair]["W"] = 0
                    results[pair]["L"] = 0
                    results[pair]["T"] = 0
                    results[pair]["Byes"] = 0
                    
                if  "result"  in pairings[pair] :

                    if "against" in pairings[pair] :
                        if pairings[pair]["against"] == -1 :
                            results[pair]["Byes"] = results[pair]["Byes"] + 1

                    
                    if  pairings[pair]["result"] == 1 :
                            results[pair]["W"] = results[pair]["W"] + 1
                        
                    elif pairings[pair]["result"] == 0 :
                            results[pair]["L"] = results[pair]["L"] + 1
    
                    elif pairings[pair]["result"] == 0.5 :
                            results[pair]["T"] = results[pair]["T"] + 1


        for result in results :
            results[result]["score"] = results[result]["W"] + (float(results[result]["T"])/2.0)        

        self.compute_median_buchholz(results, rounds)
    
        finalResult = []

        for player in results :
            p = results[player]
            p["name"] = player
            finalResult.append(p)
        
        sortedlist = sorted(finalResult, key=lambda elem: "%f %i" % (elem['score'], elem['tb']), reverse=True)


        for result in sortedlist :
            name    = result["name"]
            W       = result["W"]
            L       = result["L"]
            T       = result["T"]
            B       = result["Byes"]
            TB      = result["tb"]
            score   = result["score"]
                        
                
            text += ("<tr><td align='right'>%s</td><td align='center'>%i - %i - %i</td><td align='center'>%i</td><td align='center'>%i</td><td align='center'>%i</td></tr>" %(name, W-B,L,T, B, TB, score))

        
        text += ("</table>")
        
        
        self.score.insertHtml(text)
        
        if self.tourney.state == "finished" :
            text = "<center><font size='+3'>Supreme champion : <b>" + sortedlist[0]["name"] + "</b></font><center>"
            text += "<center><font size='+2'>Worthy Adversary : <b>" + sortedlist[1]["name"] + "</b></font><center>"
            text += "<center><font size='+1'>Maybe Next Time  : <b>" + sortedlist[2]["name"] + "</b></font><center>"
            self.finalresult.insertHtml(text)

    def inListofDict(self, list, key ,item):
        for r in list :
            if key in r :
                if r[key] == item :
                    return r
        return False 
  
    def displayBrackets(self, message):
        
        infos = message["result"]
        self.tourney.curRound = infos.get("current_rounds",1) 
        rounds = infos.get("rounds", 0)
        self.tourney.nbRounds = rounds
        pairings = infos.get("pairings", {})
        
        
        self.table.setColumnCount(int(len(self.tourney.players))/2)
        self.table.setRowCount ((rounds*2) + 1)
        
        
        self.table.setShowGrid(0)
        self.table.verticalHeader ().setVisible(0)
        self.table.horizontalHeader().setVisible(0)
        
        
        
        
        for i in range(rounds) :
            self.table.setSpan ( i*2, 0, 1, self.table.columnCount() )
            
            item =  SwissRoundItem(self, self.tourney, r=i+1)
            self.table.setItem(i*2, 0, item)
            
            self.table.setItemDelegateForRow(i*2, SwissRoundItemDelegate(self))

            
            
            players = copy.deepcopy(self.tourney.players)

            if str(i+1) in pairings :
                
                inforound = pairings[str(i+1)]

                j = 0
                for pair in inforound :
                    

                    p1 = self.inListofDict(players, "name", pair) 
                    if  p1 :
                        seed1 = p1["seed"] + 1
                        players.remove(p1)
                        
                        enemy = inforound[pair]["against"]
                        
                        p2 = self.inListofDict(players, "name", enemy) 
                        if p2 :
                            seed2 = p2["seed"] + 1
                            players.remove(p2)
                           
                            score1 = 0
                            score2 = 0

                            if "result" in inforound[pair] : 
                                
                                if inforound[pair]["result"] == 1 :
                                    score1 = 1
                                    score2 = 0
                                elif inforound[pair]["result"] == 0 :
                                    score1 = 0
                                    score2 = 1
                                elif inforound[pair]["result"] == 0.5 :
                                    score1 = .5
                                    score2 = 0.5                                    
                                                                 
                            item =  SwissBracketItem(self, self.tourney, pair, enemy, seed1, seed2, score1, score2, r=i+1)

                            self.table.setItem((i*2)+1, j, item)
                            self.table.setItemDelegateForRow((i*2)+1, SwissBracketItemDelegate(self))
                            j = j + 1
        
        
        self.table.resizeRowsToContents()
        self.table.resizeColumnsToContents()

        
        self.table.setMouseTracking(True)
        self.table.itemPressed.connect(self.bracketPressed)



class TournamentsWidget(FormClass, BaseClass):
    ''' list and manage the main tournament lister '''
    
    
    def __init__(self, client, *args, **kwargs):
        
        BaseClass.__init__(self, *args, **kwargs)        
        
        self.setupUi(self)

        self.client = client
        self.client.tourneyTab.layout().addWidget(self)
        
        #Dictionary containing our actual tournaments.
        self.tourneys = {}
        
        self.tourneyList.setItemDelegate(SwissTourneyItemDelegate(self))
        
        self.tourneyList.itemDoubleClicked.connect(self.tourneyDoubleClicked)
        self.tourneyList.itemPressed.connect(self.tourneyPressed)
                
        self.client.tourneyTypesInfo.connect(self.processTourneyTypeInfo)
        self.client.tourneyInfo.connect(self.processTourneyInfo)
        
        self.tourneyTypeList.itemDoubleClicked.connect(self.hostTourneyClicked)
        

        
        self.tourneysTab = {}
        
        self.title = ""
        self.description = ""
        self.minplayers = 2
        self.maxplayers = 99
        
        self.minrating = 0
        self.maxrating = 3000
        
        #Special stylesheet for brackets
        self.stylesheet              = util.readstylesheet("tournaments/formatters/style.css")
        
        
    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def tourneyPressed(self, item):
        if QtGui.QApplication.mouseButtons() == QtCore.Qt.RightButton:            
            #Look up the associated tourney object        
            item.pressed(item)



    @QtCore.pyqtSlot(dict)
    def processTourneyInfo(self, message):
        '''
        Slot that interprets and propagates tourney_info messages into TourneyItems 
        '''
        uid = message["uid"]
        state = message.get("state", "") 
        action = message.get("action", "")


        if uid not in self.tourneys:
            if state == "open" or state == "playing" or state == "finished":
                self.tourneys[uid] = SwissTourneyItem(self, uid)
                self.tourneyList.addItem(self.tourneys[uid])
                self.tourneys[uid].update(message, self.client)

        else:
            if state == "open" or state == "playing" or state == "finished":
                self.tourneys[uid].update(message, self.client)
                self.tourneyList.takeItem(self.tourneyList.row(self.tourneys[uid]))
                self.tourneyList.addItem(self.tourneys[uid])
                

        
        if action == "brackets" :
            # check if we've got a tourney tab for this tournament.
            if uid in self.tourneys :
                widget = None
                
                if not uid in self.tourneysTab :
                    widget = TournamentWidget(self.tourneys[uid])
                    
                    
                    self.topTabs.addTab(widget, self.tourneys[uid].title)
                   
                    self.tourneysTab[uid] = widget
                    
                    self.tourneysTab[uid].setStyleSheet(self.stylesheet)
                else :
                    widget = self.tourneysTab[uid] 
                
                widget.displayBrackets(message)
                widget.displayScores(message)
                



        #Special case: removal of a game that has ended         
        if state == "closed":
            if uid in self.tourneys :
                self.tourneyList.takeItem(self.tourneyList.row(self.tourneys[uid]))
                del self.tourneys[uid]    
            return

        
    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def tourneyDoubleClicked(self, item):
        '''
        Slot that attempts to join or leave a tournament.
        ''' 
        if not self.client.login in item.playersname :
            reply = QtGui.QMessageBox.question(self.client, "Register",
                "Do you want to register to this tournament ?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                self.client.send(dict(command="tournament", action = "join", uid=item.uid, type = item.type))
        else :
            reply = QtGui.QMessageBox.question(self.client, "Register",
                "Do you want to leave this tournament ?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:           
                self.client.send(dict(command="tournament", action = "leave", uid=item.uid, type = item.type))
        
        
    @QtCore.pyqtSlot(dict)
    def processTourneyTypeInfo(self, message):
        '''
        Slot that interprets and propagates tourney type info messages into the tourney type list 
        ''' 
        
        item = TourneyTypeItem(message)
        self.tourneyTypeList.addItem(item)       


    
    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def hostTourneyClicked(self, item):
        '''
        Hosting a tournament event
        '''
          
        hosttourneywidget = HostTourneyWidget(self, item)
        
        if hosttourneywidget.exec_() == 1 :
            if self.title != "":
                self.client.send(dict(command="create_tournament", type = item.tourney, name=self.title, min_players = self.minplayers, max_players = self.maxplayers, min_rating = self.minrating, max_rating = self.maxrating, description = self.description, date = self.date))
