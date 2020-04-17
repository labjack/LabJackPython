"""
Demonstrates I2C communication using a LabJack UE9, U6 or U3. The demonstration
uses a LJTick-DAC connected to FIO0/FIO1 for the UE9 and U6, or FIO4/FIO5 for
the U3. A read, write and again a read are performed on the LJTick-DAC's EEPROM.
"""
from random import randrange
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
                        "LJTick-DAC has a secure connection to the LabJack.")


# Comment and uncomment below code based on the LabJack you are using.
# By default the U3 is opened.
dev = u3.U3()  # Opens first found U3 over USB
#dev = u6.U6()  # Opens first found U6 over USB
#dev = ue9.UE9()  # Opens first found UE9 over USB

# EEPROM addresses for the LJTick-DAC.
EEPROM_ADDRESS = 80

# SCL amd SDA pin numbers that the LJTick-DAC are connected to.
if dev.devType == 3:
    # U3 settings
    SCL_PIN_NUM = 4  # FIO4
    SDA_PIN_NUM = 5  # FIO5

    # Configure FIO0-FIO3 as analog, and FIO4-FIO7 as digital I/O. SCL and SDA
    # lines need to be digital.
    dev.configIO(FIOAnalog=0x0F)
else:
    # UE9 and U6 settings
    SCL_PIN_NUM = 0  # FIO0
    SDA_PIN_NUM = 1  # FIO1

# Initial read of EEPROM bytes 0-3 in the user memory area. We need a single I2C
# transmission that writes the chip's memory pointer and then reads the data.
writeBytes = [0]  # Byte 0: Memory pointer = 0
writeBytesLen = len(writeBytes)
numBytesToRead = 4
ret = dev.i2c(EEPROM_ADDRESS, writeBytes, False, False, False, 0, SDA_PIN_NUM,
              SCL_PIN_NUM, numBytesToRead)
checkAck(writeBytesLen, ret["AckArray"])
print("\nRead User Memory [0-3] = %s" % ret["I2CBytes"])

# Write EEPROM bytes 0-3 in the user memory area, using the page write
# technique.  Note that page writes are limited to 16 bytes max, and must be
# aligned with the 16-byte page intervals.  For instance, if you start writing
# at address 14, you can only write two bytes because byte 16 is the start of a
# new page.
writeBytes = [0]  # Byte 0: Memory pointer = 0
# Create 4 new random numbers to write (writeBytes[1-4]).
writeBytes.extend([randrange(0, 256) for _ in range(4)])
writeBytesLen = len(writeBytes)
numBytesToRead = 0
ret = dev.i2c(EEPROM_ADDRESS, writeBytes, False, False, False, 0, SDA_PIN_NUM,
              SCL_PIN_NUM, numBytesToRead)
checkAck(writeBytesLen, ret["AckArray"])
print("\nWrite User Memory [0-3] = %s" % writeBytes[1:writeBytesLen])

# Delay to allow the EEPROM to complete the write cycle.
sleep(0.02)

# Final read of EEPROM bytes 0-3 in the user memory area. We need a single I2C
# transmission that writes the address and then reads the data.
writeBytes = [0]  # Byte 0: Memory pointer = 0
writeBytesLen = len(writeBytes)
numBytesToRead = 4
ret = dev.i2c(EEPROM_ADDRESS, writeBytes, False, False, False, 0, SDA_PIN_NUM,
              SCL_PIN_NUM, numBytesToRead)
checkAck(writeBytesLen, ret["AckArray"])
print("\nRead User Memory [0-3] = %s" % ret["I2CBytes"])

# Close the device
dev.close()
