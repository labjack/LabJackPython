"""
This example uses Python's built-in threading module to reach faster streaming 
speeds than streamTest.py.

On a Ubuntu 9.10 machine with a AMD Athlon(tm) 64 X2 Dual Core Processor 5200+,
we got speeds up to 50kHz.

On a Mac OS 10.6 machine with a 2.53 GHz Intel Core 2 Duo Processor, we got
speeds up to 50kHz.

On a Mac OS 10.5 machine with a 1.42 GHz G4 Processor, we saw max speeds of
about 40kHz.
"""

import u3, u6, LabJackPython
from time import sleep
from datetime import datetime
import struct
import threading
import Queue
import ctypes, copy, sys

# MAX_REQUESTS is the number of packets to be read.
# At high frequencies ( >5 kHz), the number of samples will be MAX_REQUESTS times 48 (packets per request) times 25 (samples per packet)
MAX_REQUESTS = 2500

d = None

################################################################################
## U3 
## Uncomment these lines to stream from a U3
################################################################################
#d = u3.U3()
#
## to learn the if the U3 is an HV
#d.configU3()
#
## Set the FIO0 to Analog
#d.configIO(FIOAnalog = 1)
#
#print "configuring U3 stream"
#d.streamConfig( NumChannels = 1, PChannels = [ 0 ], NChannels = [ 31 ], Resolution = 3, SampleFrequency = 50000 )

################################################################################
## U6
## Uncomment these lines to stream from a U6
################################################################################
#d = u6.U6()
#
## For applying the proper calibration to readings.
#d.getCalibrationData()
#
#print "configuring U6 stream"
#d.streamConfig( NumChannels = 1, ChannelNumbers = [ 0 ], ChannelOptions = [ 0 ], SettlingFactor = 1, ResolutionIndex = 1, SampleFrequency = 50000 )

if d is None:
    print "Configure a device first.\nPlease open streamTest-threading.py in a text editor and uncomment the lines for your device, starting at about line 16.\n\nExiting..."
    sys.exit(0)
    
class StreamDataReader(object):
    def __init__(self, device):
        self.device = device
        self.data = Queue.Queue()
        self.dataCount = 0
        self.missed = 0
        self.running = False
        
    def readStreamData(self):
        self.running = True
        
        start = datetime.now()
        self.device.streamStart()
        while self.running:
            # Calling with convert = False, because we are going to convert in
            # the main thread.
            returnDict = self.device.streamData(convert = False).next()
            
            self.data.put_nowait(copy.deepcopy(returnDict))
            
            self.dataCount += 1
            if self.dataCount > MAX_REQUESTS:
                self.running = False
        
        print "stream stopped."
        self.device.streamStop()
        stop = datetime.now()
        
        total = self.dataCount * self.device.packetsPerRequest * self.device.streamSamplesPerPacket
        print "%s requests with %s packets per request with %s samples per packet = %s samples total." % ( self.dataCount, d.packetsPerRequest, d.streamSamplesPerPacket, total )
        
        print "%s samples were lost due to errors." % self.missed
        total -= self.missed
        print "Adjusted number of samples = %s" % total
        
        runTime = (stop-start).seconds + float((stop-start).microseconds)/1000000
        print "The experiment took %s seconds." % runTime
        print "%s samples / %s seconds = %s Hz" % ( total, runTime, float(total)/runTime )

sdr = StreamDataReader(d)

sdrThread = threading.Thread(target = sdr.readStreamData)

# Start the stream and begin loading the result into a Queue
sdrThread.start()

errors = 0
missed = 0
while True:
    try:
        # Check if the thread is still running
        if not sdr.running:
            break
        
        # Pull results out of the Queue in a blocking manner.
        result = sdr.data.get(True, 1)
        
        # If there were errors, print that.
        if result['errors'] != 0:
            errors += result['errors']
            missed += result['missed']
            print "+++++ Total Errors: %s, Total Missed: %s" % (errors, missed)
            
        # Convert the raw bytes (result['result']) to voltage data.
        r = d.processStreamData(result['result'])
        
        # Do some processing on the data to show off.
        print "Average of", len(r['AIN0']), "reading(s):", sum(r['AIN0'])/len(r['AIN0'])

    except Queue.Empty:
        print "Queue is empty. Stopping..."
        sdr.running = False
        break
    except KeyboardInterrupt:
        sdr.running = False
    except Exception, e:
        print type(e), e
        sdr.running = False
        break
    
