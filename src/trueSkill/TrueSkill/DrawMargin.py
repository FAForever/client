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





from trueSkill.Numerics.GaussianDistribution import *
from math import sqrt

class DrawMargin :

    @staticmethod
    def getDrawMarginFromDrawProbability(drawProbability, beta) :
#
#        // Derived from TrueSkill technical report (MSR-TR-2006-80), page 6
#
#        // draw probability = 2 * CDF(margin/(sqrt(n1+n2)*beta)) -1
#
#        // implies
#        //
#        // margin = inversecdf((draw probability + 1)/2) * sqrt(n1+n2) * beta
#        // n1 and n2 are the number of players on each team


        margin = GaussianDistribution.inverseCumulativeTo(.5*(drawProbability + 1.0), 0.0, 1.0)*sqrt(1.0 + 1.0)* beta
        return margin

