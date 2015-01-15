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





INF = 1e300000
NaN = INF/INF

from math import pi as PI
from math import sqrt, fabs, log, exp


from BasicMath import square

class GaussianDistribution(object):
    def __init__(self, mean = 0.0, standardDeviation = 1.0):

        self._mean = mean
        self._standardDeviation = standardDeviation
      
        #precision and precisionMean are used because they make multiplying and dividing simpler
        #(the the accompanying math paper for more details)
        self._variance = square(standardDeviation)
        self._precision = None
        self._precisionMean = None
    
        
        if self._variance != 0.0 :
            self._precision = 1/self._variance
            self._precisionMean = self._precision * self._mean
            
        else :
            self._precision = INF
            
            if self._mean == 0.0 :
                self._precisionMean = 0.0
            else :
                self._precisionMean = INF
    
    def getMean(self):
        return self._mean
    
    def getVariance(self):
        return self._variance
    
    def getStandardDeviation(self):
        return self._standardDeviation

    def getPrecision(self):
        return self._precision
    
    def getPrecisionMean(self):
        return self._precisionMean
    
    def getNormalizationConstant(self):
        #// Great derivation of this is at http://www.astro.psu.edu/~mce/A451_2/A451/downloads/notes0.pdf
        return 1.0/(sqrt(2*PI)*self._standardDeviation)

    def __clone(self):
        result = GaussianDistribution()
        result._mean = self._mean
        result._standardDeviation = self._standardDeviation
        result._variance = self._variance
        result._precision = self._precision
        result._precisionMean = self._precisionMean
        return result

    @staticmethod
    def fromPrecisionMean( precisionMean, precision):
        result = GaussianDistribution()
        result._precision = precision
        result._precisionMean = precisionMean
        
        if precision != 0.0 :
            result._variance = 1.0/precision
            result._standardDeviation = sqrt(result._variance)
            result._mean = result._precisionMean / result._precision
        
        else :
            result._variance = INF
            result._standardDeviation = INF
            result._mean = NaN
            
        return result
    

    
    @staticmethod
    def multiply(left, right) :
        '''For details, see http://www.tina-vision.net/tina-knoppix/tina-memo/2003-003.pdf
        for multiplication, the precision mean ones are easier to write :)
        '''
        return GaussianDistribution.fromPrecisionMean(left._precisionMean + right._precisionMean, left._precision + right._precision)
    
    
#    
    @staticmethod
    def absoluteDifference(left, right) :
        '''Computes the absolute difference between two Gaussians'''
        return max(
            abs(left._precisionMean - right._precisionMean),
            sqrt(fabs(left._precision - right._precision)))

        #
    @staticmethod
    def subtract(left, right) :
        '''Computes the absolute difference between two Gaussians'''
        return GaussianDistribution.absoluteDifference(left, right)
    
    @staticmethod
    def logProductNormalization(left, right) :

        if ((left._precision == 0) or (right._precision == 0)) :
            return 0


        varianceSum = left._variance + right._variance
        meanDifference = left._mean - right._mean

        logSqrt2Pi = log(sqrt(2*PI));
        return -logSqrt2Pi - (log(varianceSum)/2.0) - (square(meanDifference)/(2.0*varianceSum))
    
    
    @staticmethod
    def divide(numerator, denominator) :
        return GaussianDistribution.fromPrecisionMean(numerator._precisionMean - denominator._precisionMean,
                                 numerator._precision - denominator._precision)
    
    
    @staticmethod
    def logRatioNormalization(numerator, denominator) :

        if ((numerator._precision == 0) or (denominator._precision == 0)) :
            return 0;

        varianceDifference = denominator._variance - numerator._variance
        meanDifference = numerator._mean - denominator._mean

        logSqrt2Pi = log(sqrt(2*PI));

        return log(denominator._variance) + logSqrt2Pi - log(varianceDifference)/2.0 + square(meanDifference)/(2*varianceDifference)

    @staticmethod
    def at( x, mean = 0.0, standardDeviation = 1.0) :
        '''
        See http://mathworld.wolfram.com/NormalDistribution.html
                        1              -(x-mean)^2 / (2*stdDev^2)
         P(x) = ------------------- * e
               stdDev * sqrt(2*pi)
            '''
        multiplier = 1.0/(standardDeviation*sqrt(2.0*PI))
        expPart = exp((-1.0*square(x - mean))/(2.0*square(standardDeviation)))
        result = multiplier*expPart;
        return result

    @staticmethod
    def cumulativeTo(x, mean = 0.0, standardDeviation = 1.0) :
        invsqrt2 = -0.707106781186547524400844362104
        result = GaussianDistribution.errorFunctionCumulativeTo(invsqrt2*x)
        return 0.5*result


    @staticmethod
    def errorFunctionCumulativeTo( x) :
        '''Derived from page 265 of Numerical Recipes 3rd Edition'''            
        z = fabs(x);

        t = 2.0/(2.0 + z)
        ty = 4.0*t - 2.0

        coefficients = (
                                -1.3026537197817094, 
                                6.4196979235649026e-1,
                                1.9476473204185836e-2, 
                                -9.561514786808631e-3, 
                                -9.46595344482036e-4,
                                3.66839497852761e-4, 
                                4.2523324806907e-5, 
                                -2.0278578112534e-5,
                                -1.624290004647e-6, 
                                1.303655835580e-6, 
                                1.5626441722e-8, 
                                -8.5238095915e-8,
                                6.529054439e-9, 
                                5.059343495e-9, 
                                -9.91364156e-10, 
                                -2.27365122e-10,
                                9.6467911e-11, 
                                2.394038e-12, 
                                -6.886027e-12, 
                                8.94487e-13, 
                                3.13092e-13,
                                -1.12708e-13, 
                                3.81e-16, 
                                7.106e-15, 
                                -1.523e-15, 
                                -9.4e-17, 
                                1.21e-16, 
                                -2.8e-17 )

        ncof = len(coefficients)
        d = 0.0
        dd = 0.0

#        
        for j in range(ncof - 1 ,0,-1) :
            tmp = d
            d = ty*d - dd + coefficients[j]
            dd = tmp


        ans = t*exp(-z*z + 0.5*(coefficients[0] + ty*d) - dd)
        
        if x >= 0 :
            return ans
        else :
            return 2 - ans

    @staticmethod
    def inverseErrorFunctionCumulativeTo( p) :
        ''' From page 265 of numerical recipes'''

        if (p >= 2.0) :
            return -100

        if (p <= 0.0) :
            return 100

        if p < 1.0 :
            pp = p
        else :
            pp = 2 - p
        
        t = sqrt(-2*log(pp/2.0)); # Initial guess
        x = -0.70711*((2.30753 + t*0.27061)/(1.0 + t*(0.99229 + t*0.04481)) - t)

        for j in range(2) :
            err = GaussianDistribution.errorFunctionCumulativeTo(x) - pp
            x = x + (err/(1.12837916709551257*exp(-square(x)) - x*err)) # // Halley                

        if p < 1.0 :
            return x
        else :
            return -x

        
    @staticmethod
    def inverseCumulativeTo(x, mean = 0.0, standardDeviation = 1.0) :
        #From numerical recipes, page 320
        return mean - sqrt(2)*standardDeviation*GaussianDistribution.inverseErrorFunctionCumulativeTo(2*x)

    def __str__(self) :
        return ("mean=%f standardDeviation=%f") % (self._mean, self._standardDeviation)
 

