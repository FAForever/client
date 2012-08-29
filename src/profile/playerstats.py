''''
THIS SHOULD BE REFACTORED BIG TIME :(

'''


from numpy.random import randn as np
from matplotlib.mlab import normpdf



import sys, os, random
from PyQt4.QtCore import *
from PyQt4.QtGui import *

#import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.dates as mdates

import datetime

from trueSkill.TrueSkill.FactorGraphTrueSkillCalculator import * 
from trueSkill.Rating import *
from trueSkill.Team import *
from trueSkill.Teams import *

import client

class Statpage(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        
        self.parent = parent
        self.parent.statsInfo.connect(self.processStatsInfos)
        
        self.globalname = None
        self.globalforevername = None

        self.tabs = QTabWidget(self)
        
        self.setCentralWidget(self.tabs)
        

        
        self.setWindowTitle('Player statistics')


        self.mu, self.sigma = 1500, 500
        self.playermu, self.playersigma = 1500, 500
        self.name = "none"
        self.create_menu()
        self.create_global_frame()
        self.create_global_evolution_frame()
        self.create_global_evolution_forever_frame()
        #self.create_status_bar()

        self.tabs.currentChanged.connect(self.tabChanged)

        self.on_draw()


    def tabChanged(self, tab):
        
        
        if tab == 1 :
            if self.name != "unknown" and self.globalname != self.name:

                self.parent.send(dict(command="stats", player=self.name, type="global_90_days"))
                self.evoaxes.clear()
                self.globalname = self.name

        if tab == 2 :
            if self.name != "unknown" and self.globalforevername != self.name:
                self.parent.send(dict(command="stats", player=self.name, type="global_forever"))
                self.evoaxesforever.clear()
                self.globalforevername = self.name
                            
    def processStatsInfos(self, message):
        print "profile"
        type = message['type']
        
        if not type == "global_forever" or not type == "global_90_days" :
            return

        name = message['player']
        
        values = message['values']
        if name == self.name :

            if type == "global_forever" :

                xaxis = []
                ymeanaxis = []
                ydevminaxis = []
                ydevmaxaxis = []
                
                for val in values :
                    ymeanaxis.append(val["mean"])
                    date = val["date"].split('.')
                    timing = val["time"].split(':')
 
                    ydevminaxis.append(val["mean"] - val["dev"])
                    ydevmaxaxis.append(val["mean"] + val["dev"])
                    
                    date = datetime.datetime(int(date[2]), int(date[1]), int(date[0]), int(timing[0]), int(timing[1]))
                    xaxis.append(date)
                

                self.evoaxesforever.clear()
                self.evoaxesforever.set_ylabel("Skill")
                self.evoaxesforever.set_xlabel("Time")
                

                self.evoaxesforever.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'))
                self.evoaxesforever.plot(xaxis, ymeanaxis, '-,', linewidth=.5, color='black')
                self.evoaxesforever.fill_between(xaxis, ymeanaxis, ydevminaxis,  interpolate=True, linewidth=0,  alpha=.5,  facecolor='red')
                self.evoaxesforever.fill_between(xaxis, ymeanaxis, ydevmaxaxis,  interpolate=True, linewidth=0,  alpha=.5,  facecolor='red') 
                #plt.fill(xaxis, ydevminaxis, 'r')

                self.evocanvasforever.draw()

            if type == "global_90_days" :

                xaxis = []
                ymeanaxis = []
                ydevminaxis = []
                ydevmaxaxis = []
                
                for val in values :
                    ymeanaxis.append(val["mean"])
                    date = val["date"].split('.')
                    timing = val["time"].split(':')
 
                    ydevminaxis.append(val["mean"] - val["dev"])
                    ydevmaxaxis.append(val["mean"] + val["dev"])
                    
                    date = datetime.datetime(int(date[2]), int(date[1]), int(date[0]), int(timing[0]), int(timing[1]))
                    xaxis.append(date)
                

                self.evoaxes.clear()
                self.evoaxes.set_ylabel("Skill")
                self.evoaxes.set_xlabel("Time")
                

                self.evoaxes.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
                self.evoaxes.plot(xaxis, ymeanaxis, '-,', linewidth=.5, color='black')
                self.evoaxes.fill_between(xaxis, ymeanaxis, ydevminaxis,  interpolate=True, linewidth=0,  alpha=.5,  facecolor='red')
                self.evoaxes.fill_between(xaxis, ymeanaxis, ydevmaxaxis,  interpolate=True, linewidth=0,  alpha=.5,  facecolor='red') 
                #plt.fill(xaxis, ydevminaxis, 'r')

                self.evocanvas.draw()

                

    def setplayer(self, name):
        
        if name in self.parent.players :
            

            self.evoaxes.clear()
            self.evoaxesforever.clear()
            self.setWindowTitle('Rating analysis of %s' % name)
            self.name = name
            
            self.mu = self.parent.players[name]["rating_mean"]
            self.sigma = self.parent.players[name]["rating_deviation"]
            
            self.playermu = self.parent.players[self.parent.login]["rating_mean"]
            self.playersigma = self.parent.players[self.parent.login]["rating_deviation"]

            self.on_draw()
            
            if self.tabs.currentIndex() == 1 :
                self.parent.send(dict(command="stats", player=self.name, type="global_90_days"))
            if self.tabs.currentIndex() == 2 :
                self.parent.send(dict(command="stats", player=self.name, type="global_forever"))            
        else :
            self.name = "unknown"
            self.mu = 0
            self.sigma = 0           
            
        
    def save_plot(self):
        file_choices = "PNG (*.png)|*.png"
        
        path = unicode(QFileDialog.getSaveFileName(self, 
                        'Save file', '', 
                        file_choices))
        if path:
            self.canvas.print_figure(path, dpi=self.dpi)
            self.statusBar().showMessage('Saved to %s' % path, 2000)
    
    
    def on_pick(self, event):

        box_points = event.artist.get_bbox().get_points()
        msg = "You've clicked on a bar with coords:\n %s" % box_points
        
        QMessageBox.information(self, "Click!", msg)
    
    def on_draw(self):
        """ Redraws the figure
        """
        str = unicode(self.textbox.text())
        
        x = self.mu + self.sigma*np(50000)

        self.axes.clear()        
        
        self.axes.grid(self.grid_cb.isChecked())
        
                
        self.axes.set_xlabel("Skill")
        self.axes.set_ylabel("Probability %")
        #self.ylabel('')
        self.axes.set_title("performance graph of %s"% self.name)


#
        ## the histogram of the data
        n, bins, patches = self.axes.hist(x, 100, normed=1, facecolor='green', alpha=0.55) 
        
        

        
        y = normpdf( bins, self.mu, self.sigma) * 100 

        text ="This is the potential rating of %s.\n66 percent chances to be between %i and %i." % (self.name,int(self.mu-self.sigma), int(self.mu+self.sigma))

        self.textbox.setText(text + "\n%.2f percent chances to be %i" % (round((max(y)*100),2), int(self.mu)))
        self.textbox.setText(self.textbox.text() + "\nThe worst rating possible is the one in the leaderboard : %i" % int(self.mu-3*self.sigma))
        
        self.axes.axis([self.mu-4*self.sigma, self.mu+4*self.sigma, 0, (100 + (max(y)*100)*1.5) / 2])
        #self.axes.hist(x, bins, normed=1, facecolor='green',)
        self.axes.plot(bins, y*100, linewidth=.5, linestyle = 'None', color = 'red', alpha = 1.0) 
        self.axes.fill(bins, y*100, 'r--', linewidth=0,  alpha=.5,  facecolor='red') 
        
        self.axes.annotate(('%s maximum rating (%i)' % (self.name, self.mu)), xy=(self.mu, max(y)*100),  xycoords='data',  xytext=(-50, 30), textcoords='offset points', arrowprops=dict(arrowstyle="wedge", facecolor='red', linewidth=0),  size = 7, alpha = 0.5, backgroundcolor='lightgrey')
        
        if not self.compare_cb.isChecked() :
            self.axes.fill_between(bins, y*100 ,0, where=bins>self.mu+self.sigma, facecolor='darkred',  interpolate=True)
            self.axes.fill_between(bins, y*100 ,0, where=bins<self.mu-self.sigma, facecolor='darkred', interpolate=True )
        

        if self.compare_cb.isChecked() :
            
            self.axes.set_title("performance graph of %s VS you " % self.name )

            x = self.playermu + self.playersigma*np(50000)
            n, bins, patches = self.axes.hist(x, 100, normed=1, facecolor='green', alpha=0.55)
            y2 = normpdf( bins, self.playermu, self.playersigma) * 100
            self.axes.axis([min(self.mu-4*self.sigma, self.playermu-4*self.playersigma) , max(self.mu+4*self.sigma, self.playermu+4*self.playersigma), 0, max((100 + (max(y)*100)*1.5) / 2,(100 + (max(y2)*100)*1.5) / 2)])
            self.axes.plot(bins, y2*100, linewidth=.5, linestyle = 'None', color = 'blue', alpha = 1.0) 
            self.axes.fill(bins, y2*100, 'r--', linewidth=0,  alpha=.5,  facecolor='blue')
            #self.axes.fill_between(bins, y2*100 ,0, where=bins>self.playermu+self.playersigma, facecolor='darkblue',  interpolate=True)
            #self.axes.fill_between(bins, y2*100 ,0, where=bins<self.playermu-self.playersigma, facecolor='darkblue', interpolate=True )            

            self.axes.annotate('Your maximum rating (%i)' % int(self.playermu), xy=(self.playermu, max(y2)*100),  xycoords='data',  xytext=(-50, 30), textcoords='offset points', arrowprops=dict(arrowstyle="wedge", facecolor='blue', linewidth=0),  size = 7, alpha = 0.5, backgroundcolor='lightgrey')
            
            text ="This is the potential rating of %s.\n66 percent chances to be between %i and %i. (you : between %i and %i)" % (self.name,int(self.mu-self.sigma), int(self.mu+self.sigma), int(self.playermu-self.playersigma), int(self.playermu+self.playersigma))
            self.textbox.setText(text + "\n%.2f percent chances to be %i (You : \n%.2f percent chances to be %i)" % (round((max(y)*100),2), int(self.mu), round((max(y2)*100),2), int(self.playermu)))
            self.textbox.setText(self.textbox.text() + "\nThe worst rating possible is the one in the leaderboard : %i (you : %i)" % (int(self.mu-3*self.sigma), int(self.playermu-3*self.playersigma)))
            
            teamsTrueskill = []
            Team1 = Team()
            Team1.addPlayer("1", Rating(self.mu, self.sigma))
            Team2 = Team()
            Team2.addPlayer("2", Rating(self.playermu, self.playersigma))
            teamsTrueskill.append(Team1)
            teamsTrueskill.append(Team2)
            gameInfo = GameInfo()
            calculator = FactorGraphTrueSkillCalculator()
            gamequality = calculator.calculateMatchQuality(gameInfo, teamsTrueskill) * 100
            self.textbox.setText(self.textbox.text() + "\nProbabilites of having a even match : %.2f percent" % gamequality )
            
            
        self.canvas.draw()
 

    def create_global_evolution_forever_frame(self):
        
        self.global_evolution_forever = QWidget()
        
        self.evoforeverfig = Figure((5.0, 4.0), dpi=self.dpi)
        self.evocanvasforever = FigureCanvas(self.evoforeverfig)
        self.evocanvasforever.setParent(self.global_evolution_forever)
        
        self.evoaxesforever = self.evoforeverfig.add_subplot(111)
        
        self.evotoolbarf = NavigationToolbar(self.evocanvasforever, self.global_evolution_forever)
        
        hbox = QHBoxLayout()

        
        vbox = QVBoxLayout()
        vbox.addWidget(self.evocanvasforever)
        vbox.addWidget(self.evotoolbarf)
        vbox.addLayout(hbox)
        
        self.global_evolution_forever.setLayout(vbox)
        
        self.tabs.addTab(self.global_evolution_forever, "Global Rating Evolution since forever")
        
    def create_global_evolution_frame(self):
        
        self.global_evolution = QWidget()
        
        self.evofig = Figure((5.0, 4.0), dpi=self.dpi)
        self.evocanvas = FigureCanvas(self.evofig)
        self.evocanvas.setParent(self.global_evolution)
        
        self.evoaxes = self.evofig.add_subplot(111)
        
        self.evotoolbar = NavigationToolbar(self.evocanvas, self.global_evolution)

        hbox = QHBoxLayout()
#        hbox.addWidget(self.textbox)
#        hbox.addWidget(self.grid_cb)

        
        vbox = QVBoxLayout()
        vbox.addWidget(self.evocanvas)
        vbox.addWidget(self.evotoolbar)
        vbox.addLayout(hbox)
        
        self.global_evolution.setLayout(vbox)

        
        self.tabs.addTab(self.global_evolution, "Global Rating Evolution for the last 90 days")
 
    def create_global_frame(self):
        
        self.global_frame = QWidget()
        
        # Create the mpl Figure and FigCanvas objects. 
        # 5x4 inches, 100 dots-per-inch
        #
        self.dpi = 100
        self.fig = Figure((5.0, 4.0), dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.global_frame)
        
        # Since we have only one plot, we can use add_axes 
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        #
        
        self.axes = self.fig.add_subplot(111)
        #self.fig.add_subplot(xlabel='Smarts')
        # Bind the 'pick' event for clicking on one of the bars
        #
        self.canvas.mpl_connect('pick_event', self.on_pick)
        
        # Create the navigation toolbar, tied to the canvas
        #
        self.mpl_toolbar = NavigationToolbar(self.canvas, self.global_frame)
        
        # Other GUI controls
        # 
        
        text ="This is the potential rating of %s.\n66 percent chances to be between %i and %i." % (self.name, int(self.mu-self.sigma), int(self.mu+self.sigma))
        self.textbox = QLabel(text)

        self.grid_cb = QCheckBox("Show &Grid")
        self.grid_cb.setChecked(True)
        self.connect(self.grid_cb, SIGNAL('stateChanged(int)'), self.on_draw)
#        

        self.compare_cb = QCheckBox("&Compare to you")
        self.connect(self.compare_cb, SIGNAL('stateChanged(int)'), self.on_draw)

        hbox = QHBoxLayout()
        

        hbox.addWidget(self.textbox)
        hbox.addWidget(self.grid_cb)
        hbox.addWidget(self.compare_cb)
        hbox.setAlignment(self.grid_cb, Qt.AlignVCenter)
        hbox.setAlignment(self.grid_cb, Qt.AlignRight)
        
        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)
        vbox.addWidget(self.mpl_toolbar)
        vbox.addLayout(hbox)
        
        self.global_frame.setLayout(vbox)
        
        self.tabs.addTab(self.global_frame, "Global rating")
        
        
        

    def create_menu(self):        
        self.file_menu = self.menuBar().addMenu("&File")
        
        load_file_action = self.create_action("&Save plot",
            shortcut="Ctrl+S", slot=self.save_plot, 
            tip="Save the plot")
        quit_action = self.create_action("&Quit", slot=self.close, 
            shortcut="Ctrl+Q", tip="Close the application")
        
        self.add_actions(self.file_menu, 
            (load_file_action, None, quit_action))
        
       


    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    def create_action(  self, text, slot=None, shortcut=None, 
                        icon=None, tip=None, checkable=False, 
                        signal="triggered()"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/%s.png" % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action
