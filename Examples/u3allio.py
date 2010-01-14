# Based on u3allio.c

import u3
from datetime import datetime
import sys

numChannels = int(sys.argv[1])
quickSample = 1
longSettling = 0

latestAinValues = [0] * numChannels

numIterations = 1000

d = u3.U3()

try:
    #Configure the IOs before the test starts
    
    FIOEIOAnalog = ( 2 ** numChannels ) - 1;
    fios = FIOEIOAnalog & (0xFF)
    eios = FIOEIOAnalog/256
    
    d.configIO( FIOAnalog = fios, EIOAnalog = eios )
    
    d.getFeedback(u3.PortDirWrite(Direction = [0, 0, 0], WriteMask = [0, 0, 15]))
    
    
    feedbackArguments = []
    
    feedbackArguments.append(u3.DAC0_8(Value = 125))
    feedbackArguments.append(u3.PortStateRead())
    
    for i in range(numChannels):
        feedbackArguments.append( u3.AIN(i, 31, QuickSample = quickSample, LongSettling = longSettling ) )
    
    #print feedbackArguments
    
    start = datetime.now()
    # Call Feedback 1000 times
    i = 0
    while i < numIterations:
        results = d.getFeedback( feedbackArguments )
        #print results
        for j in range(numChannels):
            latestAinValues[j] = d.binaryToCalibratedAnalogVoltage(results[ 2 + j ], isLowVoltage = False, isSingleEnded = True)
        i += 1

    end = datetime.now()
    delta = end - start
    print "Time difference: ", delta
    dm = delta / numIterations
    print "Time per iteration: ", dm
    print "Time per iteration in millis: ", dm.microseconds  / 1000.0
    print "Latest readings: ", latestAinValues

finally:
    d.close()