#-------------------------------------------------------------------------------
# Copyright (c) 2013 Gael Honorez.
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
# This program is distributed in the hope that i will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------

from PyQt4 import QtCore, QtGui
import util
class ReinforcementDelegate(QtGui.QStyledItemDelegate):
    
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
        
        if index.model().flags(index) == QtCore.Qt.NoItemFlags:
            icon.paint(painter, option.rect.adjusted(5-2, -2, 0, 0), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, mode=1)
        else :
            icon.paint(painter, option.rect.adjusted(5-2, -2, 0, 0), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)

        #Description
        painter.translate(option.rect.left() + iconsize.width() + 10, option.rect.top())
        clip = QtCore.QRectF(0, 0, option.rect.width()-iconsize.width() - 10 - 5, option.rect.height())
        html.drawContents(painter, clip)
        painter.restore()
        

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)        
        item = index.model().data(index, QtCore.Qt.UserRole)
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(item.TEXTWIDTH)
        
        return QtCore.QSize(item.ICONSIZE + item.TEXTWIDTH + item.PADDING, item.HEIGHT)  

class ReinforcementGroupDelegate(QtGui.QStyledItemDelegate):
    
    def __init__(self, *args, **kwargs):
        QtGui.QStyledItemDelegate.__init__(self, *args, **kwargs)
        
    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)       
        painter.save()
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        item = index.model().data(index, QtCore.Qt.UserRole)
        icon = QtGui.QIcon(option.icon)
        iconsize = icon.actualSize(option.rect.size())
        #clear icon and text before letting the control draw itself because we're rendering these parts ourselves
        option.icon = QtGui.QIcon()        
        option.text = ""  
        option.widget.style().drawControl(QtGui.QStyle.CE_ItemViewItem, option, painter, option.widget)
        
        if index.model().flags(index) == QtCore.Qt.NoItemFlags:
            icon.paint(painter, option.rect.adjusted(5-2, -2, 0, 0), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, mode=1)
        else :
            icon.paint(painter, option.rect.adjusted(5-2, -2, 0, 0), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)

        #Description
        painter.translate(option.rect.left() + iconsize.width() + 10, option.rect.top())
        clip = QtCore.QRectF(0, 0, option.rect.width()-iconsize.width() - 10 - 5, option.rect.height())
        html.drawContents(painter, clip)
        #amount
        painter.restore()
        painter.save()
        amountText = QtGui.QTextDocument()
        amountText.setHtml("<font color='red'><h2>%i</font></h2>" % item.owned)
        clip = QtCore.QRectF(0,0, amountText.size().width(), amountText.size().height())
        painter.translate(option.rect.left() + iconsize.width()-15, option.rect.top() + iconsize.height()-15)
        amountText.drawContents(painter, clip)
        #painter.drawText(QtCore.QPoint(iconsize.width()-15,iconsize.height()-15), 
        painter.restore()
        

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)        
        item = index.model().data(index, QtCore.Qt.UserRole)
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(item.TEXTWIDTH)
        
        return QtCore.QSize(item.ICONSIZE + item.TEXTWIDTH + item.PADDING, item.HEIGHT)  

class ReinforcementItem(QtGui.QListWidgetItem):
    def __init__(self, uid, small = False, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)
        self.uid            = uid
        self.name           = None
        self.price          = None
        self.activation     = None
        self.description    = None
        self.owned          = 0
        self.disabled       = False
        self.small          = small
        
        if small:
            self.FORMATTER_REINFORCEMENT       = unicode(util.readfile("galacticwar/formatters/reinforcementSmall.qthtml"))
            self.TEXTWIDTH = 100
            self.ICONSIZE = 64
            self.PADDING = 10
            self.WIDTH = self.ICONSIZE + self.TEXTWIDTH
            self.HEIGHT = 100 
        else:
            self.FORMATTER_REINFORCEMENT       = unicode(util.readfile("galacticwar/formatters/reinforcement.qthtml"))
            self.TEXTWIDTH = 370
            self.ICONSIZE = 64
            self.PADDING = 10
            self.WIDTH = self.ICONSIZE + self.TEXTWIDTH
            self.HEIGHT = 100 

        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsDragEnabled)

        self.setHidden(True)
    

    def data(self, role):
        if role == QtCore.Qt.UserRole :
            return self
        return super(ReinforcementItem, self).data(role) 
    
    def setEnabled(self):
        self.disabled       = False
        #self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsDragEnabled)
        self.setText(self.FORMATTER_REINFORCEMENT.format(color="black", owned = self.owned, name=self.name, description = self.description, activation=self.activation, price=self.price))

    def setDisabled(self):
        self.disabled       = True
        #self.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsDragEnabled)
        self.setText(self.FORMATTER_REINFORCEMENT.format(color="grey", owned = self.owned, name=self.name, description = self.description, activation=self.activation, price=self.price))
        
    def add(self, amount):
        self.owned = self.owned + amount

        if self.small :
            if self.owned == 0:
                self.setHidden(True)
            else:
                self.setHidden(False)
    
    def remove(self, amount):
        if self.owned != 0:
            self.owned = max(self.owned - amount, 0)
        
        if self.small :
            if self.owned == 0:
                self.setHidden(True)
            else:
                self.setHidden(False)
    
    def setAmount(self, amount):
        '''set amount to a precise value'''
        self.owned = amount

        if self.small :
            if self.owned == 0:
                self.setHidden(True)
            else:
                self.setHidden(False)
    
    def update(self, message, client):
        '''update this item'''
        self.client = client
        self.tech           = message["tech"]
        self.name           = message["name"]
        self.price          = message['price']
        self.delay          = message['activation']
        self.activation     = "%0.1f" % (message['activation'])
        self.description    = message["description"]
        self.owned          = message.get("owned", 0)

        iconName = "%s_icon.png" % self.uid
        icon = util.iconUnit(iconName)
        self.setIcon(icon)
        
        if message["display"] :
            self.setHidden(False)
        else:
            self.setHidden(True)
        
        if self.small and self.owned == 0:
                self.setHidden(True)

            
        self.setText(self.FORMATTER_REINFORCEMENT.format(color="black", owned = self.owned, name=self.name, description = self.description, activation=self.activation, price=self.price))
        
    def getInfos(self):
        return dict(tech=self.tech, owned=self.owned, name=self.name, price=self.price, display=True, activation=self.delay, description=self.description)
    
    def __ge__(self, other):
        ''' Comparison operator used for item list sorting '''        
        return not self.__lt__(other)
    
    
    def __lt__(self, other):
        ''' Comparison operator used for item list sorting '''        
        return self.price <= other.price