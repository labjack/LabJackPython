"""
Demonstrates how to output a sine wave using a DAC. Since we have to do it all
in software, there are limitations on how fast we can update the DAC. Update
intervals faster than 5 ms may give weird results because of the large
percentage of missed updates.

Note: The UD-Modbus interface is deprecated.

This example uses signal.setitimer() and signal.alarm(), and requires
Python 2.6 on Unix (Linux and Mac) to run. See:
http://docs.python.org/library/signal.html#signal.setitimer
http://docs.python.org/library/signal.html#signal.alarm

For a full cross-platform (Linux, Mac and Windows) example, look at the
outputSinDac.py example.

When changing the update interval and frequency, consider how your values effect
the waveform. A slow update interval coupled with a fast frequency can result in
strange behavior. Try to keep the period (1/frequency) much greater than update
interval.

Our Python interfaces throw exceptions when there are any issues with
device communications that need addressed. Many of our examples will
terminate immediately when an exception is thrown. The onus is on the API
user to address the cause of any exceptions thrown, and add exception
handling when appropriate. We create our own exception classes that are
derived from the built-in Python Exception class and can be caught as such.
For more information, see the implementation in our source code and the
Python standard documentation.
"""

import math # For sin function
import os # For name
import signal # For timing
from datetime import datetime # For printing times

import u3
import u6
import ue9


assert os.name == "posix", "This example is not compatible with Windows operating systems."

# Constants. Change these to change the results:

# Controls how fast the DAC will be updated, in seconds.
UPDATE_INTERVAL = 0.005

# The frequency of the sine wave, in Hz
FREQUENCY = 10


if __name__ == '__main__':
    print("This program will attempt to generate a sine wave with a frequency of %s Hz, updating once every %s seconds." % (FREQUENCY, UPDATE_INTERVAL))

    print("Opening LabJack...",)
    # Open up our LabJack
    d = u3.U3()
    #d = u6.U6()
    #d = ue9.UE9()

    print("Done")


    # Make a class to keep track of variables and the like
    class DacSetter(object):
        def __init__(self, frequency, updateInterval):
            self.count = 0
            self.dac = 0
            self.setDacCount = 0
            self.go = True

            # Points between peaks (pbp)
            pbp = (float(1)/frequency)/updateInterval

            # Figure out how many degrees per update we need to go.
            self.step = float(360)/pbp

            # Stupid sin function only takes radians... but I think in degrees.
            self.degToRad = ( (2*math.pi) / 360 )

        def setDac(self):
            # calculate the value to put in the sin
            value = (self.setDacCount * self.step) * self.degToRad

            # Writes the dac.
            self.dac = d.writeRegister(5000, 2.5+2*math.sin(value))

            # Count measures how many successful updates occurred.
            self.count += 1

            # Lower the go flag
            self.go = False

        def handleSetDac(self, signum, frame):
            # This function gets called every UPDATE_INTERVAL seconds.

            # Raise the go flag.
            self.go = True

            # setDacCount measures how many times the timer went off.
            self.setDacCount += 1


    # Create our DacSetter
    dacs = DacSetter(FREQUENCY, UPDATE_INTERVAL)

    # Set up the signals
    signal.signal(signal.SIGALRM, dacs.handleSetDac)
    signal.setitimer(signal.ITIMER_REAL, UPDATE_INTERVAL, UPDATE_INTERVAL)

    # Run for ~10 seconds. Expect about 2 extra seconds of overhead.
    signalcount = int(10/UPDATE_INTERVAL)

    # Print the current time, just to let you know something is happening.
    print("Start:", datetime.now())

    for i in range(signalcount):
        # Wait for signal to be received
        signal.pause()

        # If the dacs flag is set, set the DAC.
        if dacs.go:
            dacs.setDac()

    # Print the stop time, in case you wanted to know.
    print("Stop:", datetime.now())

    # Done with the timer, let's turn it off.
    signal.setitimer(signal.ITIMER_REAL, 0)

    # Print short summary of the difference between how may updates were
    # expected and how many occurred.
    print("# of Updates = %s, # of signals = %s" % (dacs.count, dacs.setDacCount))
    print("The closer the number of updates is to the number of signals, the better your waveform will be.")
