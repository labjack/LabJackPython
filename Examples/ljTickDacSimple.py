"""
Demonstrates using an LJTick-DAC with the LabJackPython modules.

"""
import struct

import u3
import u6
import ue9


class LJTickDAC:
    """Updates DACA and DACB on a LJTick-DAC connected to a U3, U6 or UE9."""
    EEPROM_ADDRESS = 0x50
    DAC_ADDRESS = 0x12

    def __init__(self, device, dioPin):
        """device: The object to an opened U3, U6 or UE9.
        dioPin: The digital I/O line that the LJTick-DAC's DIOA is connected to.

        """
        self.device = device

        # The pin numbers for the I2C command-response
        self.sclPin = dioPin
        self.sdaPin = self.sclPin + 1

        self.getCalConstants()

    def toDouble(self, buff):
        """Converts the 8 byte array into a floating point number.
        buff: An array with 8 bytes.

        """
        right, left = struct.unpack("<Ii", struct.pack("B" * 8, *buff[0:8]))
        return float(left) + float(right)/(2**32)

    def getCalConstants(self):
        """Loads or reloads the calibration constants for the LJTick-DAC.
        See datasheet for more info.

        """
        data = self.device.i2c(LJTickDAC.EEPROM_ADDRESS, [64],
                               NumI2CBytesToReceive=36, SDAPinNum=self.sdaPin,
                               SCLPinNum=self.sclPin)
        response = data['I2CBytes']
        self.slopeA = self.toDouble(response[0:8])
        self.offsetA = self.toDouble(response[8:16])
        self.slopeB = self.toDouble(response[16:24])
        self.offsetB = self.toDouble(response[24:32])

        if 255 in response:
            msg = "LJTick-DAC calibration constants seem off. Check that the " \
                  "LJTick-DAC is connected properly."
            raise Exception(msg)

    def update(self, dacA, dacB):
        """Updates the voltages on the LJTick-DAC.
        dacA: The DACA voltage to set.
        dacB: The DACB voltage to set.

        """
        binaryA = int(dacA*self.slopeA + self.offsetA)
        self.device.i2c(LJTickDAC.DAC_ADDRESS,
                        [48, binaryA // 256, binaryA % 256],
                        SDAPinNum=self.sdaPin, SCLPinNum=self.sclPin)
        binaryB = int(dacB*self.slopeB + self.offsetB)
        self.device.i2c(LJTickDAC.DAC_ADDRESS,
                        [49, binaryB // 256, binaryB % 256],
                        SDAPinNum=self.sdaPin, SCLPinNum=self.sclPin)


def openFirstFound():
    """Opens first found LabJack U6, U3 or UE9. Returns the device object on
    success or None if not found.
    """
    devices = [u6.U6, u3.U3, ue9.UE9]
    for device in devices:
        try:
            # Open the LabJack device
            return device()
        except:
            pass
    return None


# Open first found LabJack U6, U3 or UE9
dev = openFirstFound()
if dev is None:
    print("Unable to find or open a LabJack.")
    exit()
else:
    deviceTypes = {6: "U6", 3: "U3", 9: "UE9"}
    print("Found and opened a %s with serial # %s" %
          (deviceTypes[dev.devType], dev.serialNumber))

# dev = u3.U3()  # Typical way to open a first found U3
# dev = u6.U6()  # Typical way to open a first found U6
# dev = ue9.UE9()  # Typical way to open a first found UE9
dev.getCalibrationData()

# Set LJTick-DAC voltages
if dev.devType == 3:
    # For the U3, LJTick-DAC connected to FIO4 and FIO5.
    dioPin = 4
    # Configure FIO0 to FIO4 as analog inputs, and FIO04 to FIO7 as digital I/O.
    dev.configIO(FIOAnalog=0x0F)
else:
    # For the U6 and UE9, LJTick-DAC connected to FIO0 and FIO1.
    dioPin = 0
tdac = LJTickDAC(dev, dioPin)
dacA = 2.2
dacB = 3.3
tdac.update(dacA, dacB)
print("DACA and DACB set to %.5f V and %.5f V" % (dacA, dacB))

# Read voltage from AIN0
ainChan = 0
volt = dev.getAIN(ainChan)
print("AIN%s voltage = %.5f V" % (ainChan, volt))

# Close the device
dev.close()
