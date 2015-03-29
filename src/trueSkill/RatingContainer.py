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





from HashMap import *
from Player import *
from Rating import *


class RatingContainer(object):
    def __init__(self):
        self._playerToRating = HashMap()


    def getRating(self, player) :

        rating = self._playerToRating.getValue(player)
        return rating


    def setRating(self, player, rating) :

        return self._playerToRating.setValue(player, rating)


    def getAllPlayers(self) :

        allPlayers = self._playerToRating.getAllKeys()
        return allPlayers

    def getAllPlayersNames(self) :

        allPlayers = self._playerToRating.getAllKeys()
        list = []
        for player in allPlayers :
            list.append(player.getId())
        return list


    def getAllRatings(self) :

        allRatings = self._playerToRating.getAllValues()
        return allRatings


    def count(self) :
        return self._playerToRating.count()

    def __iter__(self):
        obj = []
        obj.append(self._playerToRating.getAllKeys())
        obj.append(self._playerToRating.getAllValues())

        return iter(obj)


#    def next(self):
#        list = []
#        for player in self.getAllPlayers() :
#            list.append(player)
#        for i in range(self.count()) :
#            if i == self.index :
#                return list[i]
