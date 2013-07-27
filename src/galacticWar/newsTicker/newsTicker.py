from PyQt4 import QtCore, QtGui

import sys
import copy

class NewsTicker(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        QtGui.QWidget.__init__(self, *args, **kwargs)
        
        self.news = []
        self.newNews = []
        
        self.myText = ""
        
        self.offset = 0
        self.myTimerId = 0

        self.newOnScreen = False

        self.update()
        self.updateGeometry()

    def addNews(self, news):
        for new in news :
            self.newNews.append(new)
        self.updateText() 
    
    def updateText(self):
        self.update()
        self.updateGeometry()
    
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QColor("lightGray"))
        
        
        if len(self.news) == 0  :
            if len(self.newNews) != 0 :
                self.news = copy.copy(self.newNews)
                
            return
        
        x = -self.offset
      
        loop = False
        repeat = 0

        while x < self.width() :
            
            for news in self.news + self.newNews :
                news = news + " - "
                textWidth = self.fontMetrics().width(news)
                painter.drawText(x, 0, textWidth, self.height(), QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, news)
                x = x + textWidth
            
            
            if len(self.newNews) > 0 and x > self.width() and repeat == 0 :
                for news in self.news :
                    textWidth = self.fontMetrics().width(news)
                    if textWidth < self.offset :
                        self.news.pop(0)
                        self.news.append(self.newNews[0])
                        self.newNews.pop(0)
                        break

            repeat = repeat + 1
    
    def computeWidth(self):
        text = " - ".join(self.news + self.newNews) + " - "
        return self.fontMetrics().width(text)
    
    def showEvent(self, event):
        self.myTimerId = self.startTimer(30)
        
    def timerEvent(self, event):
        if event.timerId() == self.myTimerId :
            self.offset = self.offset + 1
            
            if self.offset >= self.computeWidth() :
                self.offset = 0
            
            self.scroll(-1, 0)
            
        else :
            QtCore.QWidget.timerEvent(event)
            
            
    def hideEvent(self, event):
        self.killTimer(self.myTimerId)
        self.myTimerId = 0
         
 
    def sizeHint(self):
        text = " - ".join(self.news + self.newNews) + " - "
        return self.fontMetrics().size(0, text)

if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)
    window = NewsTicker()
    window.setMinimumSize(800,20)
    window.setMaximumSize(300,20)
    window.show()
    window.updateText()
    sys.exit(app.exec_())     