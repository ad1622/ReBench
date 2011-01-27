# Copyright (c) 2009-2011 Stefan Marr <http://www.stefan-marr.de/>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import numpy
import math
import scipy.stats.distributions as distributions


class StatisticProperties:
    """
    The statistics class calculates the statistic
    properties of a given set of data samples, i.e., the chosen values
    from a set of data points
    """
    
    def __init__(self, dataSamples, confidence_level):
        self._dataSamples = dataSamples
        self._confidenceLevel = confidence_level
        
        if self._dataSamples:
            self._calcBasicStatistics()
            self._calcConfidence(confidence_level)
            self.failedRun = False
        else:
            self.failedRun = True
            self.numSamples = 0
            
        
    def _calcBasicStatistics(self):
        """This function determines the mean and the standard deviation
           of the data sample.
           Forthermore, several other simple properties are determined.
        """
        self.mean       = numpy.mean(self._dataSamples)
        self.median     = numpy.median(self._dataSamples)
        self.stdDev     = numpy.std(self._dataSamples)
        self.numSamples = len(self._dataSamples)

        self.min = min(self._dataSamples)
        self.max = max(self._dataSamples)

    def _calcConfidence(self, confidence_level):
        """
        Depending on the number of samples, different distributions
        are more optimal.
        
        Uses normal distribution, for >30 values
        javastats used students,
        i.e., t distribution for fewer values (<=30 values)
        """
        if self.numSamples > 30:
            distribution = distributions.norm.ppf((1 + confidence_level)/2.0)
        else:
            df   = self.numSamples - 1
            distribution = distributions.t.ppf((1 + confidence_level)/2.0, df)
            
        self._confidenceForSamples(distribution)
            
    def _confidenceForSamples(self, distribution):
        """This function determines the confidence interval for a given 
           set of samples, as well as  and the size of the confidence 
           interval and its percentage of the mean.
        """
        
        self.confIntervalLow  = self.mean - (distribution * self.stdDev / math.sqrt(self.numSamples))
        self.confIntervalHigh = self.mean + (distribution * self.stdDev / math.sqrt(self.numSamples))
        
        self.confIntervalSizeAbs = self.confIntervalHigh - self.confIntervalLow
        self.confIntervalSize = self.confIntervalSizeAbs / self.mean  

