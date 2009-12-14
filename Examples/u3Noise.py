"""
" Name: u3Noise.py
" Desc: ( See below )
"""

DESC = """
This program will attempt to measure the noise of a provided signal on the U3. This is good if there is ever a question of noise from the labjack or from a signal.

The experiment is performed by taking 128 readings in quick succession. The results are then operated on the get the following values:

Peak-To-Peak Noise: The difference between the minimum and the maximum of the 128 values. Since all readings should be the same, any variation is noise.

Noise Free Resolution (bits): This represents how many bits are noise free.

Noise Free Resolution (mV): The smallest value that can be represented noise free.

Connect your signal and run this program. After, connect something with an obviously low noise signal ( like a battery ) and runt the program. If you don't have a low-noise signal, you can always jumper two FIO's to Ground and measure the noise as a differential.

You'll find that by comparing the two results, the labjack is rarely the reason for noisy readings.

On with the test:
"""

import u3
import math

def calcNoiseAndResolution(d, positiveChannel = 0, negitiveChannel = 31):
    readings = []
    
    cmd = u3.AIN(positiveChannel, negitiveChannel, QuickSample = False, LongSettling = False)
    
    for i in xrange(128):
        readings.append( float(d.getFeedback(cmd)[0])/16 )
    #print readings
    
    # Peak-To-Peak Noise
    p2pn = max(readings) - min(readings)
    
    # Noise-free resolution in bits
    if p2pn > 0:
        nfrbits = 12 - math.log(p2pn, 2)
    else:
        nfrbits = 12
    
    # Noise-free resolution in milivolts
    if d.deviceName.endswith("HV") and positiveChannel < 4:
        vRange = 20.6
    else:
        if negitiveChannel != 31:
            vRange = 4.88
        else:
            vRange = 2.44
    
    nfrres = ( vRange / (2**nfrbits) ) * (10 ** 3)
    
    return p2pn, nfrbits, nfrres
    
print DESC

pos = raw_input("Positive Channel (0-31) [0]: ")
try:
    pos = int(pos)
except:
    pos = 0

neg = raw_input("Negitive Channel (0-31) [31]: ")
try:
    neg = int(neg)
except:
    neg = 31

d = u3.U3()

results = calcNoiseAndResolution(d, pos, neg)

print "Peak-To-Peak Noise =", results[0]
print "Noise Free Resolution (bits) =", results[1]
print "Noise Free Resolution (mV) =", results[2]

d.close()