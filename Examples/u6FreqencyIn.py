"""
Demonstrates how to set up and read a timer for frequency input
See the U6 datasheet for more timer/counter info:
https://labjack.com/support/datasheets/u6/hardware-description/timers-counters
"""

import u6
from time import sleep

# Open the first found U6
d = u6.U6()
# Set the timer clock to 48MHz, no div
timerClockSpeed = 48000000
d.configTimerClock(TimerClockBase=2) # uses the low-level clock base index
# Put timer0 on FIO0
d.configIO(NumberTimersEnabled=1, TimerCounterPinOffset=0)
#Set up 32-bit period measurement on rising edges
d.getFeedback(u6.TimerConfig(timer=0, TimerMode=2, Value=0))

readDelay = 0.2 # 200ms between timer reads
numReads = 10
for i in range(numReads):
    sleep(readDelay)
    # Read timer0
    timerVal = d.getFeedback( u6.Timer(timer=0, UpdateReset=False))
    print("Period = %f ms" % (timerVal[0]*1000/timerClockSpeed))