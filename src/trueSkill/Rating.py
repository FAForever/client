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
CONSERVATIVE_STANDARD_DEVIATION_MULTIPLIER = 3

#    Container for a player's rating.
#    Constructs a rating.
#    @param double $mean The statistical mean value of the rating (also known as mu).
#    @param double $standardDeviation The standard deviation of the rating (also known as s).
#    @param double $conservativeStandardDeviationMultiplier optional The number of standardDeviations to subtract from the mean to achieve a conservative rating.

 
class Rating(object):

    def __init__(self,
                  mean, 
                standardDeviation, 
                conservativeStandardDeviationMultiplier = CONSERVATIVE_STANDARD_DEVIATION_MULTIPLIER
                ) :

        self._mean = mean
        self._standardDeviation = standardDeviation
        self._conservativeStandardDeviationMultiplier = conservativeStandardDeviationMultiplier

    def setMean(self, mean):
        self._mean = mean

    def setStandardDeviation(self, standardDeviation):
        self._standardDeviation = standardDeviation

    def getMean(self) :
        '''The statistical mean value of the rating (also known as mu).'''
        return self._mean       

    def getStandardDeviation(self) :
        '''The standard deviation (the spread) of the rating. This is also known as s.'''
        return self._standardDeviation

    def getConservativeRating(self) :
        '''A conservative estimate of skill based on the mean and standard deviation.'''
        return self._mean - self._conservativeStandardDeviationMultiplier*self._standardDeviation

    def getPartialUpdate(prior, fullPosterior, updatePercentage) :

        priorGaussian = GaussianDistribution(prior.getMean(), prior.getStandardDeviation() )
        posteriorGaussian = GaussianDistribution(fullPosterior.getMean() , fullPosterior.getStandardDeviation() )

#         From a clarification email from Ralf Herbrich:
#         "the idea is to compute a linear interpolation between the prior and posterior skills of each player 
#         ... in the canonical space of parameters"

        precisionDifference = posteriorGaussian.getPrecision()  - priorGaussian.getPrecision()
        partialPrecisionDifference = updatePercentage*precisionDifference

        precisionMeanDifference = posteriorGaussian.getPrecisionMean()  - priorGaussian.getPrecisionMean()
        partialPrecisionMeanDifference = updatePercentage*precisionMeanDifference

        partialPosteriorGaussion = GaussianDistribution.fromPrecisionMean(
            priorGaussian.getPrecisionMean()  + partialPrecisionMeanDifference,
            priorGaussian.getPrecision()  + partialPrecisionDifference)

        return Rating(partialPosteriorGaussion.getMean() , partialPosteriorGaussion.getStandardDeviation() , prior._conservativeStandardDeviationMultiplier)

    def __str__(self) :
        return "mean=%.4f, standardDeviation=%.4f" %( self._mean, self._standardDeviation)


