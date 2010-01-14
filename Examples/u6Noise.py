"""
Name: noise.py
Intended Device: U6
Desc: An example program that will calculate the values that can be found in
      Appendix B of the U6 User's Guide.
"""

import u6 # Import the u6 class
import math # Need math for square root and log.
from datetime import datetime

# The size of the various ranges
ranges = [20, 2, 0.2, 0.02]

# A nice string representation of each range
strRanges = ["+/- 10", "+/- 1", "+/- 0.1", "+/- 0.01"]

# Numerical versions of range that the LabJack expects
vRanges = range(4)

def calcNoiseAndResolution(d, resolutionIndex, voltageRange):
    """
    Takes 128 readings and calculates noise and resolution
    """
    # Make a list to hold our readings
    readings = []
    
    # The feedback command to send to the device
    cmd = u6.AIN24AR(15, ResolutionIndex = resolutionIndex, GainIndex = voltageRange, SettlingFactor = 4)
    
    start = datetime.now()
    
    # Collect 128 samples
    for i in xrange(128):
        readings.append(d.getFeedback(cmd)[0]['AIN'])
    
    finish = datetime.now()
    
    print "%s per sample" % ( (finish-start) / 128)
    
    # The Peak-To-Peak Noise is difference between the max and the min.
    p2pn = max(readings) - min(readings)
    
    # Noise-Free resolution in bits follows the formula:
    nfrbits = 24 - math.log(p2pn, 2)
    
    # Noise-Free Resolution (uV) = 
    #                            <range> / 2 ^ < Noise-Free resolution (bits) >
    nfrres = ( ranges[voltageRange] / (2**nfrbits) ) * (10 ** 6)
    
    # Get the RMS Noise by calculating the standard deviation.
    mean = sum(readings) / len(readings)
    rms = 0
    for r in readings:
        rms += (r - mean) ** 2
    rms = float(rms)/len(readings)
    rms = math.sqrt(rms)
    
    # Effective Resolution is uses a similar formulas as Noise-Free.
    erbits = 24 - math.log(rms, 2)
    
    erres = ( ranges[voltageRange] / (2**erbits) ) * (10 ** 6)
    
    return [ p2pn, nfrbits, nfrres, rms, erbits, erres ]
   

d = u6.U6()

# If you have a U6-Pro, this will run though all the Resolution Indexs
if d.deviceName.endswith("Pro"):
    rIndexes = range(1, 13)
else:
    rIndexes = range(1, 9)

for i in rIndexes:
    for r in vRanges:
        rs = calcNoiseAndResolution(d,i,r)
        print "Resolution Index = %s, Range = %s:\n\tPeak-To-Peak Noise = %s, Noise-Free Resolution (bits) = %.1f, Noise-Free Resolution (uV) = %.1f\n\tRMS Noise = %i, Effective Resolution (bits) = %.1f, Effective Resolution (uV) = %.1f\n" % (i, strRanges[r], rs[0], rs[1], rs[2], rs[3], rs[4], rs[5] )

