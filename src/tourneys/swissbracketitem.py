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

import util
import client


class SwissBracketItemDelegate(QtGui.QStyledItemDelegate):
    
    def __init__(self, *args, **kwargs):
        QtGui.QStyledItemDelegate.__init__(self, *args, **kwargs)
        
    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
                
        painter.save()
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(html.idealWidth())
       
        
        if option.state & QtGui.QStyle.State_MouseOver :
            
            backColor = QtGui.QColor("#FFFFFF")
        else :
            
            backColor = QtGui.QColor("#888888")
        
        if option.text.startswith("Round") == False and option.text != "" :
            painter.fillRect(option.rect.left()+1, option.rect.top()+1, 140, 40, backColor)
            
            painter.fillRect(option.rect.left()+1, option.rect.top()+1, 20, 40, QtGui.QColor("#777777"))
            painter.fillRect(option.rect.left()+120, option.rect.top()+1, 20, 40, QtGui.QColor("#777777"))
            
            #painter.drawRoundedRect(option.rect.left()+1, option.rect.top()+1, html.size().width()-1, html.size().height()-1, 5, 5)
            #painter.drawLine(option.rect.left()+1, (option.rect.top() + html.size().height()/2), option.rect.left()+html.size().width(),  (option.rect.top() +  html.size().height()/2))
            #painter.drawLine(option.rect.left()+20, option.rect.top()+1, option.rect.left()+20, option.rect.top()+html.size().height())
            #painter.drawLine(option.rect.left()+120, option.rect.top()+1, option.rect.left()+120,  option.rect.top()+html.size().height())
        

        option.text = ""  
        
        
        
        option.widget.style().drawControl(QtGui.QStyle.CE_ItemViewItem, option, painter, option.widget)

        painter.translate(option.rect.left(), option.rect.top())
        
        
        
        clip = QtCore.QRectF(0, 0, option.rect.width(), option.rect.height())
        html.drawContents(painter, clip)
  
        painter.restore()
        
    def createEditor(self, parent, QStyleOptionViewItem, QModelIndex):
        ''' no edit !'''
        pass

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(html.idealWidth())

        return QtCore.QSize(int(html.size().width())+25, int(html.size().height())+15)  



class SwissRoundItem(QtGui.QTableWidgetItem):
    def __init__(self, parent, tourney, r=1, *args, **kwargs):
        QtGui.QTableWidgetItem.__init__(self, *args, **kwargs)
        
        self.parent = parent
        self.itemtourney = tourney 
        self.client = tourney.client
        self.round  = r
        
        text = ("Round %i" % self.round)  
        
        self.setText(text)
   
    def validate(self):
        ''' validate the round and proceed to the next one''' 
        reply = QtGui.QMessageBox.question(self.client, "Round validation",
                "If you validate this round, you won't be able to modify scores anymore ! Do you want to proceed ?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            self.client.send(dict(command="tournament", action = "validate_round", uid=self.itemtourney.uid, type = self.itemtourney.type))

    def finish(self):
        ''' finish the tournament''' 
        reply = QtGui.QMessageBox.question(self.client, "Finish the tournament",
                "If you finish this tournament, you won't be able to modify scores anymore ! Do you want to proceed ?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            self.client.send(dict(command="tournament", action = "finish", uid=self.itemtourney.uid, type = self.itemtourney.type))


    def pressed(self, item):
        menu = QtGui.QMenu(self.parent)



        if self.itemtourney.host == self.client.login and self.itemtourney.curRound == self.round and self.itemtourney.state != "open" :
            
            if self.round == self.itemtourney.nbRounds :
                actionFinish = QtGui.QAction("Finish the tournament", menu)
                actionFinish.triggered.connect(self.finish)
                menu.addAction(actionFinish)
                menu.popup(QtGui.QCursor.pos())         

                
            else :
            
                actionValid = QtGui.QAction("Validate round", menu)
                actionValid.triggered.connect(self.validate)
                menu.addAction(actionValid)
                menu.popup(QtGui.QCursor.pos())         

            

class SwissBracketItem(QtGui.QTableWidgetItem):
    TEXTWIDTH = 500
    ICONSIZE = 110
    PADDING = 10
    
    WIDTH = ICONSIZE + TEXTWIDTH
    #DATA_PLAYERS = 32
    
    
    FORMATTER_SWISS_BRACKET = unicode(util.readfile("tournaments/formatters/swiss_bracket.qthtml"))

    
    def __init__(self, parent, tourney, player1, player2, score1=0, score2=0, r=1, *args, **kwargs):
        QtGui.QTableWidgetItem.__init__(self, *args, **kwargs)

        
        
        
        self.parent = parent
        self.itemtourney = tourney 
        self.client = tourney.client
        
        self.player1 = player1    
        self.player2 = player2
        self.round  = r
        self.score1 = score1
        self.score2 = score2
        
        
        
        self.setText(self.FORMATTER_SWISS_BRACKET.format(player1=self.player1, player2=self.player2, score1=self.score1, score2=self.score2))
        
            
    def registerScore(self):
        item, ok = QtGui.QInputDialog.getItem(self.client, "Register score", "Winner is", [self.player1, self.player2, "Draw"], 0, False)
        if ok and item:
            if item == "Draw" :
                self.client.send(dict(command="tournament", action = "register_score", player=self.player1, score = 0.5, uid=self.itemtourney.uid, type = self.itemtourney.type))
            else :
                self.client.send(dict(command="tournament", action = "register_score", player=item, score = 1, uid=self.itemtourney.uid, type = self.itemtourney.type))
        

    def pressed(self, item):
        menu = QtGui.QMenu(self.parent)
        
        
        if self.itemtourney.host == self.client.login and self.itemtourney.state != "open" and self.itemtourney.curRound == self.round :

            actionScore = QtGui.QAction("Register score", menu)
            
            
            actionScore.triggered.connect(self.registerScore)

            
            menu.addAction(actionScore)

            menu.popup(QtGui.QCursor.pos())    
    
    def update(self, message, client):
        '''
        Updates this item from the message dictionary supplied
        '''
        
        print message
        
        self.client  = client
  

    def permutations(self, items):
        """Yields all permutations of the items."""
        if items == []:
            yield []
        else:
            for i in range(len(items)):
                for j in self.permutations(items[:i] + items[i+1:]):
                    yield [items[i]] + j




    def __ge__(self, other):
        ''' Comparison operator used for item list sorting '''        
        return not self.__lt__(other)
    
    
    def __lt__(self, other):
        ''' Comparison operator used for item list sorting '''        
        if not self.client: return True # If not initialized...
        if not other.client: return False;
        
        
        # Default: Alphabetical
        return self.title.lower() < other.title.lower()
    


