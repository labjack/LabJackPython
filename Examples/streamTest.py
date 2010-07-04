import u3, u6
from time import sleep
from datetime import datetime
import struct

# MAX_REQUESTS is the number of packets to be read.
# At high frequencies ( >5 kHz), the number of samples will be MAX_REQUESTS times 48 (packets per request) times 25 (samples per packet)
MAX_REQUESTS = 75

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
#d.streamConfig( NumChannels = 1, PChannels = [ 0 ], NChannels = [ 31 ], Resolution = 3, SampleFrequency = 10000 )

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
#
#d.streamConfig( NumChannels = 1, ChannelNumbers = [ 0 ], ChannelOptions = [ 0 ], SettlingFactor = 1, ResolutionIndex = 1, SampleFrequency = 10000 )
    
try:
    start = datetime.now()
    print "start stream", start
    d.streamStart()
    
    missed = 0
    start = datetime.now()
    dataCount = 0
    byteCount = 0
    
    for r in d.streamData():
        
        if r is not None:
            # Our stop condition
            if dataCount > MAX_REQUESTS:
                break
            
            if r['errors'] != 0:
                print "Error: %s ; " % r['errors'], datetime.now()

            if r['numPackets'] != d.packetsPerRequest:
                print "----- UNDERFLOW : %s : " % r['numPackets'], datetime.now()

            if r['missed'] != 0:
                missed += r['missed']
                print "+++ Missed ", r['missed']

            # Comment out this print and do something with r
            print "Average of", len(r['AIN0']), "reading(s):", sum(r['AIN0'])/len(r['AIN0'])

            dataCount += 1


        else:
            # Got no data back from our read.
            # This only happens if your stream isn't faster than the 
            # the USB read timeout, ~1 sec.
            print "No data", datetime.now()
    
finally:
    print "stream stopped."
    stop = datetime.now()
    d.streamStop()
    d.close()

    total = dataCount * d.packetsPerRequest * d.streamSamplesPerPacket
    print "%s requests with %s packets per request with %s samples per packet = %s samples total." % ( dataCount, d.packetsPerRequest, d.streamSamplesPerPacket, total )
    print "%s samples were lost due to errors." % missed
    total -= missed
    print "Adjusted number of samples = %s" % total
    
    runTime = (stop-start).seconds + float((stop-start).microseconds)/1000000
    print "The experiment took %s seconds." % runTime
    print "%s samples / %s seconds = %s Hz" % ( total, runTime, float(total)/runTime )
    
    
