# -*- mode: python; c-basic-offset: 4; indent-tabs-mode: nil -*-
"""
For handling communication with the BMA250 accel using SPI

More info on the BMA250 can be found here:

http://www.bosch-sensortec.com/homepage/products_3/3_axis_sensors/acceleration_sensors/bma250_1/bma250


TODO: add a BMA250Reader class for threading


This BMA250 example source code is licensed under MIT X11.

   Copyright (c) 2013 Aura Labs, Inc.  http://oneaura.com/

   Permission is hereby granted, free of charge, to any person obtaining a copy
   of this software and associated documentation files (the "Software"), to deal
   in the Software without restriction, including without limitation the rights
   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
   copies of the Software, and to permit persons to whom the Software is
   furnished to do so, subject to the following conditions:

   The above copyright notice and this permission notice shall be included in
   all copies or substantial portions of the Software.

   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
   THE SOFTWARE.
"""


import u3
import u6
import ue9
import sys


PIN_NUM_UNDEFINED = -1

# registers
CHIPID_REG = 0x00
XACCEL_LSB_REG = 0x02
XACCEL_MSB_REG = 0x03
YACCEL_LSB_REG = 0x04
YACCEL_MSB_REG = 0x05
ZACCEL_LSB_REG = 0x06
ZACCEL_MSB_REG = 0x07
G_RANGE_SEL_REG = 0x0f
TEMP_REG = 0x08
BANDWIDTH_REG = 0x10
POWER_MODES_REG = 0x11

# useful masks
NEW_DATA_MASK = 0x01
ACCELDATA_MSB_MASK = 0x0200
TEMPDATA_MSB_MASK = 0x80
SIGNEXTEND_MASK = 0xfe00
READ_MASK = 0x80

# Low-power modes. Masks for Power Modes register.
SUSPEND_MASK = 0x80
LOWPOWER_MASK = 0x40

DUMMY_BYTE = 0xff

# BMA250 G range
G_RANGE = {
    '2G':  0x03, # +- 2g, resolution  3.91 mg/LSB
    '4G':  0x05, # +- 4g, resolution  7.81 mg/LSB
    '8G':  0x08, # +- 8g, resolution 15.62 mg/LSB
    '16G': 0x0c, # +-16g, resolution 31.25 mg/LSB
    }

# BMA250 bandwidth
BANDWIDTH = {
    '7.81 Hz'  : 0x08,  #    7.81 Hz, Update time 64 ms
    '15.63 Hz' : 0x09,  #   15.63 Hz, Update time 32 ms
    '31.25 Hz' : 0x0a,  #   31.25 Hz, Update time 16 ms
    '62.5 Hz'  : 0x0b,  #   62.5  Hz, Update time  8 ms
    '125 Hz'   : 0x0c,  #  125    Hz, Update time  4 ms
    '250 Hz'   : 0x0d,  #  250    Hz, Update time  2 ms
    '500 Hz'   : 0x0e,  #  500    Hz, Update time  1 ms
    '1000 Hz'  : 0x0f,  # 1000    Hz, Update time  0.5 ms
    }


class BMA250:
    """
    BMA250 class to simplify communication with BMA250 accelerometer.
    """

    U3 = 3
    U6 = 6
    UE9 = 9
    U3_STRING = "U3"
    U6_STRING = "U6"
    UE9_STRING = "UE9"
    U3_DEFAULT_CS_PIN_NUM = 4
    U3_DEFAULT_CLK_PIN_NUM = 5
    U3_DEFAULT_MISO_PIN_NUM = 6
    U3_DEFAULT_MOSI_PIN_NUM = 7
    U6_DEFAULT_CS_PIN_NUM = 0
    U6_DEFAULT_CLK_PIN_NUM = 1
    U6_DEFAULT_MISO_PIN_NUM = 2
    U6_DEFAULT_MOSI_PIN_NUM = 3
    UE9_DEFAULT_CS_PIN_NUM = 0
    UE9_DEFAULT_CLK_PIN_NUM = 1
    UE9_DEFAULT_MISO_PIN_NUM = 2
    UE9_DEFAULT_MOSI_PIN_NUM = 3
    FIO_PIN_STATE = 0  # digital

    def __init__(self,
                 device,
                 autoUpdate=True,  # be aware that autoUpdate may be slow!
                 CSPinNum=PIN_NUM_UNDEFINED,
                 CLKPinNum=PIN_NUM_UNDEFINED,
                 MISOPinNum=PIN_NUM_UNDEFINED,
                 MOSIPinNum=PIN_NUM_UNDEFINED,
                 spi_freq=100000,
                 g_range=G_RANGE['4G'],
                 bandwidth=BANDWIDTH['62.5 Hz']):

        self.device = device
        self.autoUpdate = autoUpdate
        self.g_range = g_range
        self.bandwidth = bandwidth

        self.CSPinNum = CSPinNum
        self.CLKPinNum = CLKPinNum
        self.MISOPinNum = MISOPinNum
        self.MOSIPinNum = MOSIPinNum
        self.AutoCS = True
        self.DisableDirConfig = False
        self.SPIMode = 'D'
        self.SPIClockFactor = 256 - ((1000000 / spi_freq - 10) / 10)
        assert(self.SPIClockFactor >= 0 and self.SPIClockFactor <= 256)
        self.curState = {
            'XAccel': None,
            'YAccel': None,
            'ZAccel': None,
            'Temperature': None,
            }

        # Determine device type
        if self.device.__class__.__name__ == BMA250.U3_STRING: self.deviceType = BMA250.U3
        elif self.device.__class__.__name__ == BMA250.U6_STRING: self.deviceType = BMA250.U6
        elif self.device.__class__.__name__ == BMA250.UE9_STRING: self.deviceType = BMA250.UE9
        else:
            raise TypeError('Invalid device passed. Can not get default values.')

        # If not specified otherwise, use class default for the chip select pin number
        if self.CSPinNum == -1:
            if self.deviceType == BMA250.U3: self.CSPinNum = BMA250.U3_DEFAULT_CS_PIN_NUM
            elif self.deviceType == BMA250.U6: self.CSPinNum = BMA250.U6_DEFAULT_CS_PIN_NUM
            elif self.deviceType == BMA250.UE9: self.CSPinNum = BMA250.UE9_DEFAULT_CS_PIN_NUM
            else:
                raise TypeError('Invalid device passed. Can not get default values.')

        # If not specified otherwise, use class default for the data pin number
        if self.CLKPinNum == -1:
            if self.deviceType == BMA250.U3: self.CLKPinNum = BMA250.U3_DEFAULT_CLK_PIN_NUM
            elif self.deviceType == BMA250.U6: self.CLKPinNum = BMA250.U6_DEFAULT_CLK_PIN_NUM
            elif self.deviceType == BMA250.UE9: self.CLKPinNum = BMA250.UE9_DEFAULT_CLK_PIN_NUM
            else:
                raise TypeError('Invalid device passed. Can not get default values.')

        # If not specified otherwise, use class default for the MISO pin number
        if self.MISOPinNum == -1:
            if self.deviceType == BMA250.U3: self.MISOPinNum = BMA250.U3_DEFAULT_MISO_PIN_NUM
            elif self.deviceType == BMA250.U6: self.MISOPinNum = BMA250.U6_DEFAULT_MISO_PIN_NUM
            elif self.deviceType == BMA250.UE9: self.MISOPinNum = BMA250.UE9_DEFAULT_MISO_PIN_NUM
            else:
                raise TypeError('Invalid device passed. Can not get default values.')

        # If not specified otherwise, use class default for the MOSI pin number
        if self.MOSIPinNum == -1:
            if self.deviceType == BMA250.U3: self.MOSIPinNum = BMA250.U3_DEFAULT_MOSI_PIN_NUM
            elif self.deviceType == BMA250.U6: self.MOSIPinNum = BMA250.U6_DEFAULT_MOSI_PIN_NUM
            elif self.deviceType == BMA250.UE9: self.MOSIPinNum = BMA250.UE9_DEFAULT_MOSI_PIN_NUM
            else:
                raise TypeError('Invalid device passed. Can not get default values.')

        # Set U3 pins
        if self.deviceType == BMA250.U3:
            self.device.configIO(FIOAnalog = BMA250.FIO_PIN_STATE)

        # init accel g and bw
        g_config_bytes = [G_RANGE_SEL_REG, g_range]
        self.__spi(g_config_bytes)
        bw_config_bytes = [BANDWIDTH_REG, bandwidth]
        self.__spi(bw_config_bytes)


    def update(self):
        """
        Get a fresh set of readings.
        """

        # set up the SPI command buffer
        buf = [ XACCEL_LSB_REG | READ_MASK,
                DUMMY_BYTE, # read x accel lsb
                DUMMY_BYTE, # read x accel msb
                DUMMY_BYTE, # read y accel lsb
                DUMMY_BYTE, # read y accel msb
                DUMMY_BYTE, # read z accel lsb
                DUMMY_BYTE, # read z accel msb
                DUMMY_BYTE, ] # read temperature

        result = self.__spi(buf)
        assert(result['NumSPIBytesTransferred'] == len(result['SPIBytes']))
        spibytes = result['SPIBytes']

        # read the response
        lsb = spibytes[1]
        msb = spibytes[2]
        self.curState['XAccel'] = self.__parseAccel(lsb, msb)
        lsb = spibytes[3]
        msb = spibytes[4]
        self.curState['YAccel'] = self.__parseAccel(lsb, msb)
        lsb = spibytes[5]
        msb = spibytes[6]
        self.curState['ZAccel'] = self.__parseAccel(lsb, msb)
        self.curState['Temperature'] = self.__parseTemperature(spibytes[7])


    def enableAutoUpdate(self):
        """
        Name: BMA250.enableAutoUpdate()
        Desc: Turns on automatic updating of readings
        """
        self.autoUpdate = True


    def disableAutoUpdate(self):
        """
        Name: BMA250.disableAutoUpdate()
        Desc: Turns off automatic updating of readings
        """
        self.autoUpdate = False


    def getChipID(self):
        """
        Name: BMA250.getChipID()
        Desc: Gets the BMA250 chip ID
        """
        buf = [CHIPID_REG | READ_MASK,
               DUMMY_BYTE]
        result = self.__spi(buf)
        assert(result['NumSPIBytesTransferred'] == 2)
        print result
        return result['SPIBytes'][1]


    def getXAccel(self):
        """
        Name: BMA250.getXAccel()
        Desc: Get an X acceleration reading from BMA250
        """
        if self.autoUpdate: self.update()
        return self.curState['XAccel']


    def getYAccel(self):
        """
        Name: BMA250.getYAccel()
        Desc: Get an Y acceleration reading from BMA250
        """
        if self.autoUpdate: self.update()
        return self.curState['YAccel']


    def getZAccel(self):
        """
        Name: BMA250.getZAccel()
        Desc: Get an Z acceleration reading from BMA250
        """
        if self.autoUpdate: self.update()
        return self.curState['ZAccel']


    def getTemperature(self):
        """
        Name: BMA250.getTemperature()
        Desc: Get an Z acceleration reading from BMA250
        """
        if self.autoUpdate: self.update()
        return self.curState['Temperature']


    def __spi(self, SPIBytes):
        """Short function for SPI comm with settings specified on class init.
        Returns dictionary of results from device spi function."""
        return self.device.spi(SPIBytes,
                               self.AutoCS,
                               self.DisableDirConfig,
                               self.SPIMode,
                               self.SPIClockFactor,
                               self.CSPinNum,
                               self.CLKPinNum,
                               self.MISOPinNum,
                               self.MOSIPinNum)


    def __parseAccel(self, lsb, msb):
        """Parse acceleration readings from the lsb and msb register values.
        Returns the signed accelerometer reading."""
        reading = msb << 2 | lsb >> 6
        if reading & ACCELDATA_MSB_MASK:
            # unconverted negative in two's complement, fix it
            return reading - (ACCELDATA_MSB_MASK << 1)
        else:
            return reading


    def __parseTemperature(self, reading):
        """Returns the sign-corrected temperature value."""
        if reading & TEMPDATA_MSB_MASK:
        # unconverted negative in two's complement, fix it
            return reading - (TEMPDATA_MSB_MASK << 1)
        else:
            return reading
