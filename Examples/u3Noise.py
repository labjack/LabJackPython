"""
Name: u3Noise.py
Desc: See DESC string.
"""
import math

try:
    raw_input
except NameError:  # Python 3
    raw_input = input

import u3


DESC = """
This program will attempt to measure the noise of a provided signal on the U3. This is good if there is ever a question of noise from the LabJack or from a signal.

The experiment is performed by taking 128 readings in quick succession. The results are then operated on the get the following values:

Peak-To-Peak Noise: The difference between the minimum and the maximum of the 128 values. Since all readings should be the same, any variation is noise.

Noise-Free Resolution (bits): This represents how many bits are noise free.

Noise-Free Resolution (mV): The smallest value that can be represented noise-free.

Connect your signal and run this program. After, connect something with an obviously low-noise signal (like a battery) and run the program. If you don't have a low-noise signal, you can always jumper two FIOs to Ground and measure the noise as a differential.

You'll find that by comparing the two results, the LabJack is rarely the reason for noisy readings.

On with the test:
"""


def calcNoiseAndResolution(d, positiveChannel=0, negativeChannel=31):
    readings = []

    cmd = u3.AIN(positiveChannel, negativeChannel, QuickSample=False, LongSettling=False)

    for i in range(128):
        readings.append(float(d.getFeedback(cmd)[0]) / 16.0)
    #print readings

    # Peak-To-Peak Noise
    p2pn = max(readings) - min(readings)

    # Noise-free resolution in bits
    if p2pn > 0:
        nfrbits = 12 - math.log(p2pn, 2)
    else:
        nfrbits = 12

    # Noise-free resolution in millivolts
    if d.deviceName.endswith("HV") and positiveChannel < 4:
        vRange = 20.6
    else:
        if negativeChannel != 31:
            vRange = 4.88
        else:
            vRange = 2.44

    nfrres = (vRange / (2**nfrbits)) * (10 ** 3)

    return p2pn, nfrbits, nfrres


print(DESC)

pos = raw_input("Positive Channel (0-15, 30, 31) [0]: ")
try:
    pos = int(pos)
except:
    pos = 0

neg = raw_input("Negative Channel (0-15, 30, 31) [31]: ")
try:
    neg = int(neg)
except:
    neg = 31

# Open first found U3
d = u3.U3()

# Configure all FIO and EIO lines to analog inputs.
d.configIO(FIOAnalog=0xFF, EIOAnalog=0xFF)

results = calcNoiseAndResolution(d, pos, neg)

print("Peak-To-Peak Noise = %s" % results[0])
print("Noise-Free Resolution (bits) = %s" % results[1])
print("Noise-Free Resolution (mV) = %s" % results[2])

d.close()
