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
       
        
        if option.text.startswith("Round") == False and option.text != "" :
            painter.fillRect(option.rect.left()+1, option.rect.top()+1, 140, 40, QtGui.QColor("#888888"))
            
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
        

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(html.idealWidth())

        return QtCore.QSize(int(html.size().width())+25, int(html.size().height())+15)  





class SwissBracketItem(QtGui.QTableWidgetItem):
    TEXTWIDTH = 500
    ICONSIZE = 110
    PADDING = 10
    
    WIDTH = ICONSIZE + TEXTWIDTH
    #DATA_PLAYERS = 32
    
    
    FORMATTER_SWISS_BRACKET = unicode(util.readfile("tournaments/formatters/swiss_bracket.qthtml"))

    
    def __init__(self, parent, player1, player2, r, *args, **kwargs):
        QtGui.QTableWidgetItem.__init__(self, *args, **kwargs)

        
        
        self.parent = parent
        
        self.stylesheet              = util.readstylesheet("tournaments/formatters/style.css")
        self.player1 = player1    
        self.player2 = player2
        self.round  = r
        self.score1 = 0
        self.score2 = 0
        
        
        
        self.setText(self.FORMATTER_SWISS_BRACKET.format(player1=self.player1, player2=self.player2, score1=self.score1, score2=self.score2))
        
        #self.setHidden(True)

    
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
    


