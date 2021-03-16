"""
Demonstrates I2C communication using a LabJack UE9, U6 or U3. The demonstration
uses an SHT3x based probe connected to FIO0/FIO1/FIO2 for the UE9 and U6, or
FIO4/FIO5/FIO6 for the U3. A write only transaction for single shot acquisition
and a subsequent read only transaction are performed.
"""
from time import sleep

import u3
import u6
import ue9


def checkAck(numBytesSent, ackArray):
    """
    Name: checkAck(numBytesSent, ackArray)
    Desc: Based on the number of bytes sent in the I2C command, checks if
    the I2C response's ackArray is correct. Raises an exception if not.
    """
    if len(ackArray) != 4:
        raise Exception("Invalid AckArray %s" % (ackArray))
    ackValue = 0
    for i in range(4):
        ackValue += ackArray[i]<<(i*8)
    expectedAckValue = 2**(numBytesSent+1) - 1
    if ackValue != expectedAckValue:
        # Make sure your I2C
        raise Exception("ACK error. Expected " + str(expectedAckValue) +
                        ", received " + str(ackValue) + ".  Make sure your " \
                        "SHT3x has a secure connection to the LabJack.")


# Comment and uncomment the code below based on the LabJack you are using.
# By default the U3 is opened.
# dev = u3.U3()  # Opens first found U3 over USB
# dev = u6.U6()  # Opens first found U6 over USB
dev = ue9.UE9()  # Opens first found UE9 over USB

# SHT3x address. This could be 0x45 depending on the address pin voltage
SHT3X_ADDRESS = 0x44 # 0x44 indicates the ADDR pin is connected to a logic low
SPEED_THROTTLE = 20 # Use a roughly 70kHz clock speed

# SCL, SDA, and power pin numbers that the SHT3x are connected to.
if dev.devType == 3:
    # U3 settings
    SCL_PIN_NUM = 4  # FIO4
    SDA_PIN_NUM = 5  # FIO5
    POWER_PIN_NUM = 6 #FIO6

    # Configure FIO0-FIO3 as analog, and FIO4-FIO7 as digital I/O. SCL and SDA
    # lines need to be digital.
    dev.configIO(FIOAnalog=0x0F)
else:
    # UE9 and U6 settings
    SCL_PIN_NUM = 0  # FIO0
    SDA_PIN_NUM = 1  # FIO1
    POWER_PIN_NUM = 2 #FIO2

# Set a pin to output high to provide sensor power
if dev.devType == 9:
    dev.singleIO(1, POWER_PIN_NUM, Dir=1, State=1)
else:
    dev.setDOState(POWER_PIN_NUM, 1)

# 0x24 = clock stretching disabled, 0x00 = high repeatability
writeBytes = [0x24, 0x00]
writeBytesLen = len(writeBytes)
# Write the single shot command
ret = dev.i2c(SHT3X_ADDRESS, writeBytes, False, False, False, SPEED_THROTTLE, SDA_PIN_NUM,
              SCL_PIN_NUM, 0)
checkAck(writeBytesLen, ret["AckArray"])

# The sensor needs at least 15ms for the measurement. Wait 20ms
sleep(.02)

# SHT3x sensors should always return 6 bytes for single shot acquisition: 
# temp MSB, temp LSB, CRC, RH MSB, RH LSB, CRC
numBytesToRead = 6
writeBytes = []
# Do a read only command to get the tempC and RH data
ret = dev.i2c(SHT3X_ADDRESS, writeBytes, False, False, False, SPEED_THROTTLE, SDA_PIN_NUM,
              SCL_PIN_NUM, numBytesToRead)
checkAck(0, ret["AckArray"])

# Convert the temperature and RH binary to appropriate measurement units
temp = ret["I2CBytes"][0]*256 + ret["I2CBytes"][1]
tempC = 175*temp / 65535 - 45
rh = ret["I2CBytes"][3]*256 + ret["I2CBytes"][4]
rh = 100*rh / 65535
print("tempC = %f degC, RH = %f%%\n" % (tempC, rh))
 
# Close the device
dev.close()
