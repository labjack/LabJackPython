"""
Note: Our Python interfaces throw exceptions when there are any issues with
device communications that need addressed. Many of our examples will
terminate immediately when an exception is thrown. The onus is on the API
user to address the cause of any exceptions thrown, and add exception
handling when appropriate. We create our own exception classes that are
derived from the built-in Python Exception class and can be caught as such.
For more information, see the implementation in our source code and the
Python standard documentation.
"""

import sys
from datetime import datetime

import u6


try:
    numChannels = int(sys.argv[1])
except:
    print("Missing or invalid integer value argument that specifies the number of analog inputs.")
    print("Exiting.")
    sys.exit()
resolutionIndex = 1
gainIndex = 0
settlingFactor = 0
differential = False

latestAinValues = [0] * numChannels

numIterations = 1000

d = u6.U6()
d.getCalibrationData()

try:
    # Configure the IOs before the test starts

    FIOEIOAnalog = (2 ** numChannels) - 1
    fios = FIOEIOAnalog & 0xFF
    eios = FIOEIOAnalog // 256

    d.getFeedback(u6.PortDirWrite(Direction=[0, 0, 0], WriteMask=[0, 0, 15]))

    feedbackArguments = []

    feedbackArguments.append(u6.DAC0_8(Value=125))
    feedbackArguments.append(u6.PortStateRead())

    for i in range(numChannels):
        feedbackArguments.append(u6.AIN24(i, resolutionIndex, gainIndex, settlingFactor, differential))

    start = datetime.now()
    # Call Feedback 1000 (default) times
    i = 0
    while i < numIterations:
        results = d.getFeedback(feedbackArguments)
        for j in range(numChannels):
            latestAinValues[j] = d.binaryToCalibratedAnalogVoltage(gainIndex, results[2 + j])
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
