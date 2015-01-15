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
from math import fabs

class TruncatedGaussianCorrectionFunctions :

#    // These functions from the bottom of page 4 of the TrueSkill paper.
#
#    /**
#     * The "V" function where the team performance difference is greater than the draw margin.
#     * 
#     * In the reference F# implementation, this is referred to as "the additive
#     * correction of a single-sided truncated Gaussian with unit variance."
#     * 
#     * @param number $drawMargin In the paper, it's referred to as just "".
#     */
    @staticmethod
    def vExceedsMarginScaled(teamPerformanceDifference, drawMargin, c) :
        return TruncatedGaussianCorrectionFunctions.vExceedsMargin(teamPerformanceDifference/c, drawMargin/c)

    @staticmethod
    def vExceedsMargin(teamPerformanceDifference, drawMargin) :

        denominator = GaussianDistribution.cumulativeTo(teamPerformanceDifference - drawMargin)

        if (denominator < 2.222758749e-162) :

            return -teamPerformanceDifference + drawMargin

        return GaussianDistribution.at(teamPerformanceDifference - drawMargin)/denominator


#    /**
#     * The "W" function where the team performance difference is greater than the draw margin.
#     * 
#     * In the reference F# implementation, this is referred to as "the multiplicative
#     * correction of a single-sided truncated Gaussian with unit variance."
#     */
#    
    @staticmethod
    def wExceedsMarginScaled(teamPerformanceDifference, drawMargin, c) :

        return TruncatedGaussianCorrectionFunctions.wExceedsMargin(teamPerformanceDifference/c, drawMargin/c)

    @staticmethod
    def wExceedsMargin(teamPerformanceDifference, drawMargin) :

        denominator = GaussianDistribution.cumulativeTo(teamPerformanceDifference - drawMargin)

        if (denominator < 2.222758749e-162) :

            if (teamPerformanceDifference < 0.0) :

                return 1.0

            return 0.0

        vWin = TruncatedGaussianCorrectionFunctions.vExceedsMargin(teamPerformanceDifference, drawMargin)
        return vWin*(vWin + teamPerformanceDifference - drawMargin)
 

    #// the additive correction of a double-sided truncated Gaussian with unit variance
    @staticmethod
    def vWithinMarginScaled(teamPerformanceDifference, drawMargin, c) :

        return TruncatedGaussianCorrectionFunctions.vWithinMargin(teamPerformanceDifference/c, drawMargin/c)

    
    #
    @staticmethod
    def vWithinMargin(teamPerformanceDifference, drawMargin) :

        teamPerformanceDifferenceAbsoluteValue = fabs(teamPerformanceDifference)
        denominator = GaussianDistribution.cumulativeTo(drawMargin - teamPerformanceDifferenceAbsoluteValue) - GaussianDistribution.cumulativeTo(-drawMargin - teamPerformanceDifferenceAbsoluteValue)

        if (denominator < 2.222758749e-162) :

            if (teamPerformanceDifference < 0.0) :

                return -teamPerformanceDifference - drawMargin


            return -teamPerformanceDifference + drawMargin


        numerator = GaussianDistribution.at(-drawMargin - teamPerformanceDifferenceAbsoluteValue) - GaussianDistribution.at(drawMargin - teamPerformanceDifferenceAbsoluteValue)

        if (teamPerformanceDifference < 0.0) :

            return -numerator/denominator


        return numerator/denominator


#    // the multiplicative correction of a double-sided truncated Gaussian with unit variance
    @staticmethod
    def wWithinMarginScaled(teamPerformanceDifference, drawMargin, c) :

        return TruncatedGaussianCorrectionFunctions.wWithinMargin(teamPerformanceDifference/c, drawMargin/c)


#    // From F#:
    @staticmethod
    def wWithinMargin(teamPerformanceDifference, drawMargin) :

        teamPerformanceDifferenceAbsoluteValue = fabs(teamPerformanceDifference);
        denominator = GaussianDistribution.cumulativeTo(drawMargin - teamPerformanceDifferenceAbsoluteValue) - GaussianDistribution.cumulativeTo(-drawMargin - teamPerformanceDifferenceAbsoluteValue)

        if (denominator < 2.222758749e-162) :

            return 1.0;


        vt = TruncatedGaussianCorrectionFunctions.vWithinMargin(teamPerformanceDifferenceAbsoluteValue, drawMargin) 

        return vt*vt + ((drawMargin - teamPerformanceDifferenceAbsoluteValue)*GaussianDistribution.at(drawMargin - teamPerformanceDifferenceAbsoluteValue)  - (-drawMargin - teamPerformanceDifferenceAbsoluteValue) * GaussianDistribution.at(-drawMargin - teamPerformanceDifferenceAbsoluteValue))/denominator
