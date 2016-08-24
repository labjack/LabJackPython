"""
This example uses Python's built-in threading module to help reach faster
streaming speeds than streamTest.py.
"""
import sys
import threading
import time

from copy import deepcopy
from datetime import datetime

try:
    import Queue
except ImportError:  # Python 3
    import queue as Queue

import u3
import u6
import ue9


# MAX_REQUESTS is the number of packets to be read.
MAX_REQUESTS = 2500
# SCAN_FREQUENCY is the scan frequency of stream mode in Hz.
SCAN_FREQUENCY = 50000

d = None

###############################################################################
# U3
# Uncomment these lines to stream from a U3
###############################################################################
'''
# At high frequencies ( >5 kHz), the number of samples will be MAX_REQUESTS
# times 48 (packets per request) times 25 (samples per packet)
d = u3.U3()

# To learn the if the U3 is an HV
d.configU3()

# For applying the proper calibration to readings.
d.getCalibrationData()

# Set the FIO0 to Analog
d.configIO(FIOAnalog=1)

print("Configuring U3 stream")
d.streamConfig(NumChannels=1, PChannels=[0], NChannels=[31], Resolution=3, ScanFrequency=SCAN_FREQUENCY)
'''

###############################################################################
# U6
# Uncomment these lines to stream from a U6
###############################################################################
'''
# At high frequencies ( >5 kHz), the number of samples will be MAX_REQUESTS
# times 48 (packets per request) times 25 (samples per packet)
d = u6.U6()

# For applying the proper calibration to readings.
d.getCalibrationData()

print("Configuring U6 stream")
d.streamConfig(NumChannels=1, ChannelNumbers=[0], ChannelOptions=[0], SettlingFactor=1, ResolutionIndex=1, ScanFrequency=SCAN_FREQUENCY)
'''

###############################################################################
# UE9
# Uncomment these lines to stream from a UE9
###############################################################################
'''
# Changing MAX_REQUESTS to something higher for more samples.
MAX_REQUESTS = 10000

# At 200 Hz or higher frequencies, the number of samples will be MAX_REQUESTS
# times 8 (packets per request) times 16 (samples per packet).
d = ue9.UE9()
#d = ue9.UE9(ethernet=True, ipAddress="192.168.1.226")  # Over TCP/ethernet connect to UE9 with IP address 192.168.1.209

# For applying the proper calibration to readings.
d.getCalibrationData()

print("Configuring UE9 stream")

d.streamConfig(NumChannels=1, ChannelNumbers=[0], ChannelOptions=[0], SettlingTime=0, Resolution=12, ScanFrequency=SCAN_FREQUENCY)
'''

if d is None:
    print("""Configure a device first.
Please open streamTest-threading.py in a text editor and uncomment the lines for your device.

Exiting...""")
    sys.exit(0)


class StreamDataReader(object):
    def __init__(self, device):
        self.device = device
        self.data = Queue.Queue()
        self.dataCount = 0
        self.missed = 0
        self.finished = False

    def readStreamData(self):
        self.finished = False

        print("Start stream.")
        start = datetime.now()
        try:
            self.device.streamStart()
            while not self.finished:
                # Calling with convert = False, because we are going to convert in
                # the main thread.
                returnDict = next(self.device.streamData(convert=False))
                #returnDict = self.device.streamData(convert=False).next()  # Python 2.5
                if returnDict is None:
                    print("No stream data")
                    continue

                self.data.put_nowait(deepcopy(returnDict))

                self.missed += returnDict["missed"]
                self.dataCount += 1
                if self.dataCount >= MAX_REQUESTS:
                    self.finished = True

            print("Stream stopped.\n")
            self.device.streamStop()
            stop = datetime.now()

            # Delay to help prevent print text overlapping in the two threads.
            time.sleep(0.200)

            sampleTotal = self.dataCount * self.device.packetsPerRequest * self.device.streamSamplesPerPacket
            scanTotal = sampleTotal / 1  # sampleTotal / NumChannels

            print("%s requests with %s packets per request with %s samples per packet = %s samples total." %
                  (self.dataCount, d.packetsPerRequest, d.streamSamplesPerPacket, sampleTotal))

            print("%s samples were lost due to errors." % self.missed)
            sampleTotal -= self.missed
            print("Adjusted number of samples = %s" % sampleTotal)

            runTime = (stop-start).seconds + float((stop-start).microseconds)/1000000
            print("The experiment took %s seconds." % runTime)
            print("Actual Scan Rate = %s Hz" % SCAN_FREQUENCY)
            print("Timed Scan Rate = %s scans / %s seconds = %s Hz" %
                  (scanTotal, runTime, float(scanTotal)/runTime))
            print("Timed Sample Rate = %s samples / %s seconds = %s Hz" %
                  (sampleTotal, runTime, float(sampleTotal)/runTime))
        except Exception:
            try:
                # Try to stop stream mode. Ignore exception if it fails.
                self.device.streamStop()
            except:
                pass
            self.finished = True
            e = sys.exc_info()[1]
            print("readStreamData exception: %s %s" % (type(e), e))


sdr = StreamDataReader(d)

sdrThread = threading.Thread(target=sdr.readStreamData)

# Start the stream and begin loading the result into a Queue
sdrThread.start()

errors = 0
missed = 0
# Read from Queue until there is no data. Adjust Queue.get timeout
# for slow scan rates.
while True:
    try:
        # Pull results out of the Queue in a blocking manner.
        result = sdr.data.get(True, 1)

        # If there were errors, print that.
        if result["errors"] != 0:
            errors += result["errors"]
            missed += result["missed"]
            print("+++++ Total Errors: %s, Total Missed: %s +++++" % (errors, missed))

        # Convert the raw bytes (result['result']) to voltage data.
        r = d.processStreamData(result['result'])

        # Do some processing on the data to show off.
        print("Average of %s reading(s): %s" % (len(r['AIN0']), sum(r['AIN0'])/len(r['AIN0'])))
    except Queue.Empty:
        if sdr.finished:
            print("Done reading from the Queue.")
        else:
            print("Queue is empty. Stopping...")
            sdr.finished = True
        break
    except KeyboardInterrupt:
        sdr.finished = True
    except Exception:
        e = sys.exc_info()[1]
        print("main exception: %s %s" % (type(e), e))
        sdr.finished = True
        break

# Wait for the stream thread to stop
sdrThread.join()

# Close the device
d.close()
