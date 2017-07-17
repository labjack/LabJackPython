"""
Demonstrates how to output a sine wave using DAC0. Since we have to do it all
in software, there are limitations on how fast we can update the DAC. Update
intervals faster than 5 ms may give weird results because of the large
percentage of missed updates.

When changing the update interval and frequency, consider how your values effect
the waveform. A slow update interval coupled with a fast frequency can result in
strange behavior. Try to keep the period (1/frequency) much greater than update
interval.

"""

import math  # For sin
import sys  # For version_info and platform
import time  # For sleep, clock, time and perf_counter
from datetime import datetime  # For printing times with now

import u3
import u6
import ue9


# Select the time function based on Python version and operating system.
# Use timenow for time afterwards.
if (sys.version_info < (3, 3)):
    # Python version < 3.3
    if sys.platform.startswith("win32"):
        # Windows
        timenow = time.clock
    else:
        # Linux/Mac
        timenow = time.time
else:
    # Python version >= 3.3
    timenow = time.perf_counter


class DacSinGenerator(object):
    """Generates a sine wave on DAC0 of a LabJack U3, U6 or UE9. """
    def __init__(self, device, frequency, updateInterval, runTime):
        """device: U3, U6 or UE9 object.
        frequency: Sine wave frequency, in hertz.
        updateInterval: DAC update interval, in seconds.
        runTime: Amount of time to run the sine wave, in seconds.

        """
        self.count = 0  # DAC update count
        self.dacAddress = 5000  # DAC Modbus address
        self.setDacCount = 0  # DAC update count used. Based on time.
        self.updateInterval = float(updateInterval)
        self.runTime = float(runTime)

        # Points between peaks (pbp)
        pbp = (float(1)/frequency)/self.updateInterval

        # Degrees per update step
        self.step = float(360)/pbp

        # For degrees to radians conversion
        self.degToRad = ((2*math.pi) / 360)

    def setDac(self):
        """Set the DAC value on the LabJack. Called by run. """
        # Calculate the value to put in the sin.
        value = (self.setDacCount * self.step) * self.degToRad

        # Set DAC voltage
        d.writeRegister(self.dacAddress, 2.5+2*math.sin(value))

        # Increment DAC update count
        self.count += 1

    def run(self):
        """Runs the sine generator. Takes about updateInterval time."""
        startTime = timenow()
        nextTime = startTime
        while (timenow() - startTime) < self.runTime:
            curTime = timenow()
            nextTimeChanged = False
            while nextTime <= curTime:
                # If this loops more than once, we missed an update.
                nextTime += self.updateInterval
                nextTimeChanged = True

            sleepTime = nextTime - curTime
            time.sleep(sleepTime)

            if not nextTimeChanged:
                # Repeat update detected. Skip.
                continue

            self.setDacCount = int(round((timenow() - startTime) / self.updateInterval))
            self.setDac()


if __name__ == "__main__":
    print("Opening LabJack...")

    # Open first found LabJack U6, U3 or UE9
    d = None
    devs = [u6.U6, u3.U3, ue9.UE9]
    devTypes = {6: "U6", 3: "U3", 9: "UE9"}
    for dev in devs:
        try:
            # Open LabJack
            d = dev()
            print("Found and opened a %s with serial # %s" %
                  (devTypes[d.devType], d.serialNumber))
            break
        except:
            pass
    if d is None:
        print("Unable to find or open a LabJack.")
        exit()

    # Create sine wave generator
    updateInterval = 0.005  # In seconds
    frequency = 10  # In Hz
    runTime = 10  # In seconds
    sinGen = DacSinGenerator(d, frequency, updateInterval, runTime)

    print("This program will attempt to generate a sine wave with a frequency" \
          " of %s Hz, updating once every %s seconds. This will take about" \
          " %s seconds to run." % (frequency, updateInterval, runTime))

    print("Start: %s" % datetime.now())

    # Run sine wave generator
    sinGen.run()

    print("Stop: %s" % datetime.now())

    print("# of updates = %s, # of signals = %s" %
          (sinGen.count, sinGen.setDacCount))
    print("The closer the number of updates is to the number of signals, " \
          "the better your waveform will be.")
