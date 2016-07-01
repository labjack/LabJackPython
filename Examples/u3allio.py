# Based on u3allio.c

import sys
from datetime import datetime

import u3


try:
    numChannels = int(sys.argv[1])
except:
    print("Missing or invalid integer value argument that specifies the number of analog inputs.")
    print("Exiting.")
    sys.exit()
quickSample = 1
longSettling = 0
latestAinValues = [0] * numChannels
numIterations = 1000

d = u3.U3()
d.getCalibrationData()

try:
    # Configure the IOs before the test starts

    FIOEIOAnalog = (2 ** numChannels) - 1
    fios = FIOEIOAnalog & 0xFF
    eios = FIOEIOAnalog // 256
    d.configIO(FIOAnalog=fios, EIOAnalog=eios)

    d.getFeedback(u3.PortDirWrite(Direction=[0, 0, 0], WriteMask=[0, 0, 15]))

    feedbackArguments = []
    feedbackArguments.append(u3.DAC0_8(Value=125))
    feedbackArguments.append(u3.PortStateRead())

    # Check if the U3 is an HV
    if d.configU3()['VersionInfo'] & 18 == 18:
        isHV = True
    else:
        isHV = False

    for i in range(numChannels):
        feedbackArguments.append(u3.AIN(i, 31, QuickSample=quickSample, LongSettling=longSettling))

    start = datetime.now()
    # Call Feedback 1000 (default) times
    i = 0
    while i < numIterations:
        results = d.getFeedback(feedbackArguments)
        for j in range(numChannels):
            # Figure out if the channel is low or high voltage to use the correct calibration
            if isHV is True and j < 4:
                lowVoltage = False
            else:
                lowVoltage = True
            latestAinValues[j] = d.binaryToCalibratedAnalogVoltage(results[2 + j], isLowVoltage=lowVoltage, isSingleEnded=True)
        i += 1

    end = datetime.now()
    delta = end - start
    print("Time difference: %s" % delta)
    dm = delta / numIterations
    print("Time per iteration: %s" % dm)
    print("Time per iteration in millis: %s" % (dm.microseconds / 1000.0))
    print("Last readings: %s" % latestAinValues)
finally:
    d.close()
