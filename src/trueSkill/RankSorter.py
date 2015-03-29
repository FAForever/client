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





class RankSorter :

#    /**
#     * Performs an in-place sort of the items in according to the score in a decreasing order.
#     *
#     * @param $items The items to sort according to the order specified by ranks.
#     * @param $scores The score for each item where bigger is better
#     */
    @staticmethod
    def sort(teams, teamScores) :

        scores, teams = zip(*sorted(zip(teamScores, teams), reverse = True))
        return scores, teams


