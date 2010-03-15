""" Runs through the whole range of PWM Duty Cycles 

For the complete modbus map, visit the Modbus support page:
    http://labjack.com/support/Modbus

Note: Low-level commands that are commented out work only for U6/U3. UE9 is a
      little more complicated.
"""
import u3, u6, ue9
from time import sleep

# Open the LabJack. Comment out all but one of these:
d = ue9.UE9()
#d = u3.U3()
#d = u6.U6()

if d.devType == 9:
    # Set the timer clock to be the system clock with a given divisor
    d.writeRegister(7000, 1)
    d.writeRegister(7002, 15)
else:
    # Set the timer clock to be 4 MHz with a given divisor
    #d.configTimerClock( TimerClockBase = 4, TimerClockDivisor = 15)
    d.writeRegister(7000, 4)
    d.writeRegister(7002, 15)

# Enable the timer
#d.configIO( NumberTimersEnabled = 1 )
d.writeRegister(50501, 1)

# Configure the timer for PWM, starting with a duty cycle of 0.0015%.
baseValue = 65535
#d.getFeedback( u6.Timer0Config(TimerMode = 0, Value = baseValue) )
d.writeRegister(7100, [0, baseValue])

# Loop, updating the duty cycle every time.
for i in range(65):
    currentValue = baseValue - (i * 1000)
    dutyCycle = ( float(65536 - currentValue) / 65535 ) * 100
    print "Duty Cycle = %s%%" % dutyCycle
    #d.getFeedback( u6.Timer0( Value = currentValue, UpdateReset = True ) )
    d.writeRegister(7200, currentValue)
    sleep(0.3)
print "Duty Cycle = 100%"
#d.getFeedback( u6.Timer0( Value = 0, UpdateReset = True ) )
d.writeRegister(7200, 0)

# Close the device.
d.close