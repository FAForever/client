from PyQt4 import QtCore, QtGui

import sys
import copy

class NewsTicker(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        QtGui.QWidget.__init__(self, *args, **kwargs)
        
        self.news = []
        
        self.myText = ""
        
        self.offset = 0
        self.myTimerId = 0

        self.newOnScreen = False

        self.update()
        self.updateGeometry()

    def addNews(self, news):
        for new in news :
            if not new in self.news:
                self.news.append(new)
    
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QColor("lightGray"))
        
        
        if len(self.news) == 0  :
            return

        if len(self.news) > 20 :
            toRemoveWidth = self.computeWidth(self.news[0] + " - ")
            if self.offset >= toRemoveWidth:
                self.offset = self.offset - toRemoveWidth
                self.news.pop(0)

        x = -self.offset
        while x < self.width() :
            
            for news in self.news :
                news = news + " - "
                textWidth = self.fontMetrics().width(news)

                painter.drawText(x, 0, textWidth, self.height(), QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, news)
                x = x + textWidth

            


    def computeWidth(self, text):
        return self.fontMetrics().width(text)
    
    def showEvent(self, event):
        self.myTimerId = self.startTimer(30)
        
    def timerEvent(self, event):
        if event.timerId() == self.myTimerId :
            self.offset = self.offset + 1
            
            if self.offset >= self.computeWidth(text = " - ".join(self.news) + " - ") :
                self.offset = 0
            
            self.scroll(-1, 0)
            
        else :
            QtCore.QWidget.timerEvent(event)
            
            
    def hideEvent(self, event):
        self.killTimer(self.myTimerId)
        self.myTimerId = 0
         
 
    def sizeHint(self):
        text = " - ".join(self.news) + " - "
        return self.fontMetrics().size(0, text)

    