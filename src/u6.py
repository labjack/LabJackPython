"""
" A U6 class to hold helper functions. Inspired by u3.py
"
"""
from LabJackPython import *

import struct

def toDouble(buffer):
    """
    Name: toDouble(buffer)
    Args: buffer, an array with 8 bytes
    Desc: Converts the 8 byte array into a floating point number.
    """
    if type(buffer) == type(''):
        bufferStr = buffer[:8]
    else:
        bufferStr = ''.join(chr(x) for x in buffer[:8])
    dec, wh = struct.unpack('<Ii', bufferStr)
    return float(wh) + float(dec)/2**32

def dumpPacket(buffer):
    """
    Name: dumpPacket(buffer)
    Args: byte array
    Desc: Returns hex value of all bytes in the buffer
    """
    return repr([ hex(x) for x in buffer ])

def getBit(n, bit):
    """
    Name: getBit(n, bit)
    Args: n, the original integer you want the bit of
          bit, the index of the bit you want
    Desc: Returns the bit at position "bit" of integer "n"
    
    >>> n = 5
    >>> bit = 2
    >>> getBit(n, bit)
    1
    >>> bit = 0
    >>> getBit(n, bit)
    1

    """
    return int(bool((int(n) & (1 << bit)) >> bit))

def toBitList(inbyte):
    """
    Name: toBitList(inbyte)
    Args: a byte
    Desc: Converts a byte into list for access to individual bits
    
    >>> inbyte = 5
    >>> toBitList(inbyte)
    [1, 0, 1, 0, 0, 0, 0, 0]
    
    """
    return [ getBit(inbyte, b) for b in range(8) ]

def dictAsString(d):
    """Helper function that returns a string representation of a dictionary"""
    s = "{"
    for key, val in sorted(d.items()):
        s += "%s: %s, " % (key, val)
    s = s.rstrip(", ")  # Nuke the trailing comma
    s += "}"
    return s

class CalibrationInfo(object):
    """ A class to hold the calibration info for a U6 """
    def __init__(self):
        # Positive Channel calibration
        self.ain10vSlope = 3.1580578 * (10 ** -4)
        self.ain10vOffset = -10.5869565220
        self.ain1vSlope = 3.1580578 * (10 ** -5)
        self.ain1vOffset = -1.05869565220
        self.ain100mvSlope = 3.1580578 * (10 ** -6)
        self.ain100mvOffset = -0.105869565220
        self.ain10mvSlope = 3.1580578 * (10 ** -7)
        self.ain10mvOffset = -0.0105869565220
        
        self.ainSlope = [self.ain10vSlope, self.ain1vSlope, self.ain100mvSlope, self.ain10mvSlope]
        self.ainOffset = [ self.ain10vOffset, self.ain1vOffset, self.ain100mvOffset, self.ain10mvOffset ]
        
        # Negative Channel calibration
        self.ain10vNegSlope = -3.15805800 * (10 ** -4)
        self.ain10vCenter = 33523.0
        self.ain1vNegSlope = -3.15805800 * (10 ** -5)
        self.ain1vCenter = 33523.0
        self.ain100mvNegSlope = -3.15805800 * (10 ** -6)
        self.ain100mvCenter = 33523.0
        self.ain10mvNegSlope = -3.15805800 * (10 ** -7)
        self.ain10mvCenter = 33523.0
        
        self.ainNegSlope = [ self.ain10vNegSlope, self.ain1vNegSlope, self.ain100mvNegSlope, self.ain10mvNegSlope ]
        self.ainCenter = [ self.ain10vCenter, self.ain1vCenter, self.ain100mvCenter, self.ain10mvCenter ]
        
        # Miscellaneous
        self.dac0Slope = 13200.0
        self.dac0Offset = 0
        self.dac1Slope = 13200.0
        self.dac1Offset = 0
        
        self.currentOutput0 = 0.0000100000
        self.currentOutput1 = 0.0002000000
        
        self.temperatureSlope = -92.379
        self.temperatureOffset = 465.129
        
        # Hi-Res ADC stuff
        # Positive Channel calibration
        self.proAin10vSlope = 3.1580578 * (10 ** -4)
        self.proAin10vOffset = -10.5869565220
        self.proAin1vSlope = 3.1580578 * (10 ** -5)
        self.proAin1vOffset = -1.05869565220
        self.proAin100mvSlope = 3.1580578 * (10 ** -6)
        self.proAin100mvOffset = -0.105869565220
        self.proAin10mvSlope = 3.1580578 * (10 ** -7)
        self.proAin10mvOffset = -0.0105869565220
        
        # Negative Channel calibration
        self.proAin10vNegSlope = -3.15805800 * (10 ** -4)
        self.proAin10vCenter = 33523.0
        self.proAin1vNegSlope = -3.15805800 * (10 ** -5)
        self.proAin1vCenter = 33523.0
        self.proAin100mvNegSlope = -3.15805800 * (10 ** -6)
        self.proAin100mvCenter = 33523.0
        self.proAin10mvNegSlope = -3.15805800 * (10 ** -7)
        self.proAin10mvCenter = 33523.0
    
    def __str__(self):
        return str(self.__dict__)

class U6(Device):
    """ A Python class that represents a U6 """
    def __init__(self, debug = False):
        """
        Name: U6.__init__(self, debug = False)
        Args: debug, Do you want debug information?
        Desc: Your basic constructor.
        """
        self.devType = 6
        self.firmwareVersion = 0
        self.bootloaderVersion = 0
        self.hardwareVersion = 0
        self.serialNumber = 0
        self.productId = 0
        self.localId = 0
        self.fioDirection = [None] * 8
        self.fioState = [None] * 8
        self.eioDirection = [None] * 8
        self.eioState = [None] * 8
        self.cioDirection = [None] * 8
        self.cioState = [None] * 8
        self.dac1Enable = 0
        self.dac0 = 0
        self.dac1 = 0
        self.handle = 0
        self.calInfo = CalibrationInfo()
        self.productName = "U6"
        self.debug = debug

    def open(self, localId = None, firstFound = True, devNumber = None, handleOnly = False):
        """
        Name: U6.open(localId = None, firstFound = True)
        Args: firstFound, use the first found U6?
              localId, open this local id
        Desc: Opens a U6 for reading.
        
        >>> myU6 = U6()
        >>> myU6.openU6()
        """
        Device.open(self, 6, firstFound = firstFound, localId = localId, devNumber = devNumber, handleOnly = handleOnly )
    
    def configU6(self, LocalID = None):
        """
        Name: U6.configU6(LocalID = None)
        Args: LocalID, if set, will write the new value to U6
        Desc: Writes the Local ID, and reads some hardware information.
        
        >>> myU6 = u6.U6()
        >>> myU6.open()
        >>> myU6.configU6()
        {'BootloaderVersion': '6.15',
         'FirmwareVersion': '0.88',
         'HardwareVersion': '2.0',
         'LocalID': 1,
         'ProductID': 6,
         'SerialNumber': 360005087,
         'VersionInfo': 4}
        """
        command = [ 0 ] * 26
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x0A
        command[3] = 0x08
        #command[4]  = Checksum16 (LSB)
        #command[5]  = Checksum16 (MSB)
        
        if LocalID != None:
            command[6] = (1 << 3)
            command[8] = LocalID
            
        #command[7] = Reserved
        
        #command[9-25] = Reserved 
        
        result = self._writeRead(command, 38, [0xF8, 0x10, 0x08])
        
        self.firmwareVersion = "%s.%s" % (result[10], result[9])
        self.bootloaderVersion = "%s.%s" % (result[12], result[11]) 
        self.hardwareVersion = "%s.%s" % (result[14], result[13])
        self.serialNumber = struct.unpack("<I", struct.pack(">BBBB", *result[15:19]))[0]
        self.productId = struct.unpack("<H", struct.pack(">BB", *result[19:21]))[0]
        self.localId = result[21]
        self.versionInfo = result[37]
        self.deviceName = 'U6'
        if self.versionInfo == 12:
            self.deviceName = 'U6-Pro'
        
        return { 'FirmwareVersion' : self.firmwareVersion, 'BootloaderVersion' : self.bootloaderVersion, 'HardwareVersion' : self.hardwareVersion, 'SerialNumber' : self.serialNumber, 'ProductID' : self.productId, 'LocalID' : self.localId, 'VersionInfo' : self.versionInfo, 'DeviceName' : self.deviceName }
        
    def configIO(self, NumberTimersEnabled = None, EnableCounter1 = None, EnableCounter0 = None, TimerCounterPinOffset = None):
        """
        Name: U6.configIO(NumberTimersEnabled = None, EnableCounter1 = None, EnableCounter0 = None, TimerCounterPinOffset = None)
        Args: NumberTimersEnabled, Number of timers to enable
              EnableCounter1, Set to True to enable counter 1, F to disable
              EnableCounter0, Set to True to enable counter 0, F to disable
              TimerCounterPinOffset, where should the timers/counters start
              
              if all args are None, command just reads.
              
        Desc: Writes and reads the current IO configuration.
        
        >>> myU6 = u6.U6()
        >>> myU6.open()
        >>> myU6.configIO()
        {'Counter0Enabled': False,
         'Counter1Enabled': False,
         'NumberTimersEnabled': 0,
         'TimerCounterPinOffset': 0}
        """
        command = [ 0 ] * 16
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x05
        command[3] = 0x0B
        #command[4]  = Checksum16 (LSB)
        #command[5]  = Checksum16 (MSB)
        
        if NumberTimersEnabled != None:
            command[6] = 1
            command[7] = NumberTimersEnabled
        
        if EnableCounter0 != None:
            command[6] = 1
            
            if EnableCounter0:
                command[8] = 1
        
        if EnableCounter1 != None:
            command[6] = 1
            
            if EnableCounter1:
                command[8] |= (1 << 1)
        
        if TimerCounterPinOffset != None:
            command[6] = 1
            command[9] = TimerCounterPinOffset
        
        result = self._writeRead(command, 16, [0xf8, 0x05, 0x0B])
        
        print result
        
        return { 'NumberTimersEnabled' : result[8], 'Counter0Enabled' : bool(result[9] & 1), 'Counter1Enabled' : bool( (result[9] >> 1) & 1), 'TimerCounterPinOffset' : result[10] }
        
    def configTimerClock(self, TimerClockBase = None, TimerClockDivisor = None):
        """
        Name: U6.configTimerClock(TimerClockBase = None, TimerClockDivisor = None)
        Args: TimerClockBase, which timer base to use
              TimerClockDivisor, set the divisor
              
              if all args are None, command just reads.
              Also, if you cannot set the divisor without setting the base.
              
        Desc: Writes and read the timer clock configuration.
        
        >>> myU6 = u6.U6()
        >>> myU6.open()
        >>> myU6.configTimerClock()
        {'TimeClockDivisor': 256, 'TimerClockBase': 2}
        """
        command = [ 0 ] * 10
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x02
        command[3] = 0x0A
        #command[4]  = Checksum16 (LSB)
        #command[5]  = Checksum16 (MSB)
        #command[6]  = Reserved
        #command[7]  = Reserved
        
        if TimerClockBase != None:
            command[8] = (1 << 7)
            command[8] |= TimerClockBase & 7
        
        if TimerClockDivisor != None:
            command[9] = TimerClockDivisor
            
        result = self._writeRead(command, 10, [0xF8, 0x2, 0x0A])
        
        divisor = result[9]
        if divisor == 0:
            divisor = 256
        return { 'TimerClockBase' : (result[8] & 7), 'TimeClockDivisor' : divisor }

    def _buildBuffer(self, sendBuffer, readLen, commandlist):
        for cmd in commandlist:
            if isinstance(cmd, FeedbackCommand):
                sendBuffer += cmd.cmdBytes
                readLen += cmd.readLen
            elif isinstance(cmd, list):
                sendBuffer, readLen = self._buildBuffer(sendBuffer, readLen, cmd)
        return (sendBuffer, readLen)
                
    def _buildFeedbackResults(self, rcvBuffer, commandlist, results, i):
        for cmd in commandlist:
            if isinstance(cmd, FeedbackCommand):
                results.append(cmd.handle(rcvBuffer[i:i+cmd.readLen]))
                i += cmd.readLen
            elif isinstance(cmd, list):
                self._buildFeedbackResults(rcvBuffer, cmd, results, i)
        return results

    def getFeedback(self, *commandlist):
        """
        Name: getFeedback(commandlist)
        Args: the FeedbackCommands to run
        Desc: Forms the commandlist into a packet, sends it to the U3, and reads the response.
        
        >>> myU6 = U6()
        >>> myU6.open()
        >>> ledCommand = u6.LED(False)
        >>> internalTempCommand = u6.AIN(30, 31, True)
        >>> myU6.getFeedback(ledCommand, internalTempCommand)
        [None, 23200]

        OR if you like the list version better:
        
        >>> myU6 = U6()
        >>> myU6.open()
        >>> ledCommand = u6.LED(False)
        >>> internalTempCommand = u6.AIN(30, 31, True)
        >>> commandList = [ ledCommand, internalTempCommand ]
        >>> myU6.getFeedback(commandList)
        [None, 23200]
        
        """
        
        sendBuffer = [0] * 7
        sendBuffer[1] = 0xF8
        readLen = 9
        sendBuffer, readLen = self._buildBuffer(sendBuffer, readLen, commandlist)
        if len(sendBuffer) % 2:
            sendBuffer += [0]
        sendBuffer[2] = len(sendBuffer) / 2 - 3
        
        self.write(sendBuffer)
        if readLen % 2:
            readLen += 1

        rcvBuffer = self.read(readLen)
        results = []
        i = 9
        return self._buildFeedbackResults(rcvBuffer, commandlist, results, i)

    def readMem(self, BlockNum, ReadCal=False):
        """
        Name: U6.readMem(BlockNum, ReadCal=False)
        Args: BlockNum, which block to read
              ReadCal, set to True to read the calibration data
        Desc: Reads 1 block (32 bytes) from the non-volatile user or 
              calibration memory. Please read section 5.2.6 of the user's
              guide before you do something you may regret.
        
        >>> myU6 = U6()
        >>> myU6.open()
        >>> myU6.readMem(0)
        [ < userdata stored in block 0 > ]
        
        NOTE: Do not call this function while streaming.
        """
        command = [ 0 ] * 8
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x01
        command[3] = 0x2A
        if ReadCal:
            command[3] = 0x2D
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        command[6] = 0x00
        command[7] = BlockNum
        
        result = self._writeRead(command, 40, [ 0xF8, 0x11, command[3] ])
        
        return result[8:]
    
    def readCal(self, BlockNum):
        return self.readMem(BlockNum, ReadCal = True)
        
    def writeMem(self, BlockNum, Data, WriteCal=False):
        """
        Name: U6.writeMem(BlockNum, Data, WriteCal=False)
        Args: BlockNum, which block to write
              Data, a list of bytes to write
              WriteCal, set to True to write calibration.
        Desc: Writes 1 block (32 bytes) from the non-volatile user or 
              calibration memory. Please read section 5.2.7 of the user's
              guide before you do something you may regret.
        
        >>> myU6 = U6()
        >>> myU6.open()
        >>> myU6.writeMem(0, [ < userdata to be stored in block 0 > ])
        
        NOTE: Do not call this function while streaming.
        """
        if not isinstance(Data, list):
            raise LabJackException("Data must be a list of bytes")
        
        command = [ 0 ] * 40
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x11
        command[3] = 0x28
        if WriteCal:
            command[3] = 0x2B
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        command[6] = 0x00
        command[7] = BlockNum
        command[8:] = Data
        
        self._writeRead(command, 8, [0xF8, 0x11, command[3]])

    def writeCal(self, BlockNum, Data):
        return self.writeMem(BlockNum, Data, WriteCal = True)
        
    def eraseMem(self, EraseCal=False):
        """
        Name: U6.eraseMem(EraseCal=False)
        Args: EraseCal, set to True to erase the calibration memory.
        Desc: The U6 uses flash memory that must be erased before writing.
              Please read section 5.2.8 of the user's guide before you do
              something you may regret.
        
        >>> myU6 = U6()
        >>> myU6.open()
        >>> myU6.eraseMem()
        
        NOTE: Do not call this function while streaming.
        """
        if eraseCal:
            command = [ 0 ] * 8
            
            #command[0] = Checksum8
            command[1] = 0xF8
            command[2] = 0x01
            command[3] = 0x2C
            #command[4] = Checksum16 (LSB)
            #command[5] = Checksum16 (MSB)
            command[6] = 0x4C
            command[7] = 0x6C
        else:
            command = [ 0 ] * 6
            
            #command[0] = Checksum8
            command[1] = 0xF8
            command[2] = 0x00
            command[3] = 0x29
            #command[4] = Checksum16 (LSB)
            #command[5] = Checksum16 (MSB)
        
        self._writeRead(command, 8, [0xF8, 0x01, command[3]])
    
    def eraseCal(self):
        return self.eraseMem(EraseCal=True)
    
    def setDefaults(self, SetToFactoryDefaults = False):
        """
        Name: U6.setDefaults(SetToFactoryDefaults = False)
        Args: SetToFactoryDefaults, set to True reset to factory defaults.
        Desc: Executing this function causes the current or last used values
              (or the factory defaults) to be stored in flash as the power-up
              defaults.
        
        >>> myU6 = U6()
        >>> myU6.open()
        >>> myU6.setDefaults()
        """
        command = [ 0 ] * 8
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x01
        command[3] = 0x0E
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        command[6] = 0xBA
        command[7] = 0x26
        
        if SetToFactoryDefaults:
            command[6] = 0x82
            command[7] = 0xC7
        
        self._writeRead(command, 8, [ 0xF8, 0x01, 0x0E ] )
        
    def setToFactoryDefaults(self):
        return self.setDefaults(SetToFactoryDefaults = True)
    
    validDefaultBlocks = range(8)
    def readDefaults(self, BlockNum):
        """
        Name: U6.readDefaults(BlockNum)
        Args: BlockNum, which block to read. Must be 0-7.
        Desc: Reads the power-up defaults from flash.
        
        >>> myU6 = U6()
        >>> myU6.open()
        >>> myU6.readDefaults(0)
        [ 0, 0, ... , 0]        
        """
        if BlockNum not in validDefaultBlocks:
            raise LabJackException("Defaults must be in range 0-7")
        
        command = [ 0, 0xF8, 0x01, 0x0E, 0, 0, 0, BlockNum ]
        
        result = self._writeRead(command, 40, [ 0xF8, 0x11, 0x0E ])
        
        return result[8:]
    
    def streamConfig(self, NumChannels = 1, ResolutionIndex = 0, SamplesPerPacket = 25, SettlingFactor = 0, InternalStreamClockFrequency = 0, DivideClockBy256 = False, ScanInterval = 1, ChannelNumbers = [0], ChannelOptions = [0], SampleFrequency = None):
        """
        Name: U6.streamConfig(
                 NumChannels = 1, ResolutionIndex = 0,
                 SamplesPerPacket = 25, SettlingFactor = 0,
                 InternalStreamClockFrequency = 0, DivideClockBy256 = False,
                 ScanInterval = 1, ChannelNumbers = [0],
                 ChannelOptions = [0], SampleFrequency = None )
        Args: NumChannels, the number of channels to stream
              ResolutionIndex, the resolution of the samples
              SettlingFactor, the settling factor to be used
              ChannelNumbers, a list of channel numbers to stream
              ChannelOptions, a list of channel options bytes
              
              Set Either:
              
              SampleFrequency, the frequency in Hz to sample
              
              -- OR --
              
              SamplesPerPacket, how many samples make one packet
              InternalStreamClockFrequency, 0 = 4 MHz, 1 = 48 MHz
              DivideClockBy256, True = divide the clock by 256
              ScanInterval, clock/ScanInterval = frequency.
        Desc: Configures streaming on the U6. On a decent machine, you can
              expect to stream a range of 0.238 Hz to 15 Hz. Without the
              conversion, you can get up to 55 Hz.
        
        """
        if NumChannels != len(ChannelNumbers) or NumChannels != len(ChannelOptions):
            raise LabJackException("NumChannels must match length of ChannelNumbers and ChannelOptions")
        if len(ChannelNumbers) != len(ChannelOptions):
            raise LabJackException("len(ChannelNumbers) doesn't match len(ChannelOptions)")
            
            
        if SampleFrequency != None:
            if SampleFrequency < 1000:
                if SampleFrequency < 25:
                    SamplesPerPacket = SampleFrequency
                DivideClockBy256 = True
                ScanInterval = 15625/SampleFrequency
            else:
                DivideClockBy256 = False
                ScanInterval = 4000000/SampleFrequency
        
        # Force Scan Interval into correct range
        ScanInterval = min( ScanInterval, 65535 )
        ScanInterval = int( ScanInterval )
        ScanInterval = max( ScanInterval, 1 )
        
        # Same with Samples per packet
        SamplesPerPacket = max( SamplesPerPacket, 1)
        SamplesPerPacket = int( SamplesPerPacket )
        SamplesPerPacket = min ( SamplesPerPacket, 25)
        
        command = [ 0 ] * (14 + NumChannels*2)
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = NumChannels+4
        command[3] = 0x11
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        command[6] = NumChannels
        command[7] = ResolutionIndex
        command[8] = SamplesPerPacket
        #command[9] = Reserved
        command[10] = SettlingFactor
        command[11] = (InternalStreamClockFrequency & 1) << 3
        if DivideClockBy256:
            command[11] |= 1 << 1
        t = struct.pack("<H", ScanInterval)
        command[12] = ord(t[0])
        command[13] = ord(t[1])
        for i in range(NumChannels):
            command[14+(i*2)] = ChannelNumbers[i]
            command[15+(i*2)] = ChannelOptions[i]
        
        
        self._writeRead(command, 8, [0xF8, 0x01, 0x11])
        
        # Set up the variables for future use.
        self.streamSamplesPerPacket = SamplesPerPacket
        self.streamChannelNumbers = ChannelNumbers
        self.streamChannelOptions = ChannelOptions
        self.streamConfiged = True
        
        if InternalStreamClockFrequency == 1:
            freq = float(48000000)
        else:
            freq = float(4000000)
        
        if DivideClockBy256:
            freq /= 256
        
        freq = freq/ScanInterval
        
        self.packetsPerRequest = max(1, int(freq/SamplesPerPacket))
        self.packetsPerRequest = min(self.packetsPerRequest, 48)
    
    def processStreamData(self, result):
        """
        Name: U6.processStreamData(result)
        Args: result, the string returned from streamData()
        Desc: Breaks stream data into individual channels and applies
              calibrations.
              
        >>> reading = d.streamData(convert = False)
        >>> print proccessStreamData(reading['result'])
        defaultDict(list, {'AIN0' : [3.123, 3.231, 3.232, ...]})
        """
        numBytes = 14 + (self.streamSamplesPerPacket * len(self.streamChannelNumbers) * 2)
        numPackets = len(result) // numBytes
        
        returnDict = collections.defaultdict(list)
                
        j = 0
        for packet in self.breakupPackets(result, numBytes):
            for sample in self.samplesFromPacket(packet):
                if j >= len(self.streamChannelNumbers):
                    j = 0
                
                if (self.streamChannelOptions[j] >> 7) == 1:
                    # do signed
                    value = struct.unpack('<h', sample )[0]
                else:
                    # do unsigned
                    value = struct.unpack('<H', sample )[0]
                
                gainIndex = (self.streamChannelOptions[j] >> 4) & 0x3
                value = self.binaryToCalibratedAnalogVoltage(gainIndex, value, is16Bits=True)
                
                returnDict["AIN%s" % self.streamChannelNumbers[j]].append(value)
            
                j += 1

        return returnDict
        
    def watchdog(self, Write = False, ResetOnTimeout = False, SetDIOStateOnTimeout = False, TimeoutPeriod = 60, DIOState = 0, DIONumber = 0):
        """
        Name: U6.watchdog(Write = False, ResetOnTimeout = False, SetDIOStateOnTimeout = False, TimeoutPeriod = 60, DIOState = 0, DIONumber = 0)
        Args: Write, Set to True to write new values to the watchdog.
              ResetOnTimeout, True means reset the device on timeout
              SetDIOStateOnTimeout, True means set the sate of a DIO on timeout
              TimeoutPeriod, Time, in seconds, to wait before timing out.
              DIOState, 1 = High, 0 = Low
              DIONumber, which DIO to set.
        Desc: Controls a firmware based watchdog timer.
        """
        command = [ 0 ] * 16
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x05
        command[3] = 0x09
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        if Write:
            command[6] = 1
        if ResetOnTimeout:
            command[7] = (1 << 5)
        if SetDIOStateOnTimeout:
            command[7] |= (1 << 4)
        
        t = struct.pack("<H", TimeoutPeriod)
        command[8] = ord(t[0])
        command[9] = ord(t[1])
        command[10] = ((DIOState & 1 ) << 7)
        command[10] |= (DIONumber & 0xf)
        
        result = self._writeRead(command, 16, [ 0xF8, 0x05, 0x09])
        
        watchdogStatus = {}
        
        if result[7] == 0:
            watchdogStatus['WatchDogEnabled'] = False
            watchdogStatus['ResetOnTimeout'] = False
            watchdogStatus['SetDIOStateOnTimeout'] = False
        else:
            watchdogStatus['WatchDogEnabled'] = True
            
            if (( result[7] >> 5 ) & 1):
                watchdogStatus['ResetOnTimeout'] = True
            else:
                watchdogStatus['ResetOnTimeout'] = False
                
            if (( result[7] >> 4 ) & 1):
                watchdogStatus['SetDIOStateOnTimeout'] = True
            else:
                watchdogStatus['SetDIOStateOnTimeout'] = False
        
        watchdogStatus['TimeoutPeriod'] = struct.unpack('<H', struct.pack("BB", *result[8:10]))
        
        if (( result[10] >> 7 ) & 1):
            watchdogStatus['DIOState'] = 1
        else:
            watchdogStatus['DIOState'] = 0 
        
        watchdogStatus['DIONumber'] = ( result[10] & 15 )
        
        return watchdogStatus

    SPIModes = { 'A' : 0, 'B' : 1, 'C' : 2, 'D' : 3 }
    def spi(self, SPIBytes, AutoCS=True, DisableDirConfig = False, SPIMode = 'A', SPIClockFactor = 0, CSPINNum = 0, CLKPinNum = 1, MISOPinNum = 2, MOSIPinNum = 3):
        """
        Name: U6.spi(SPIBytes, AutoCS=True, DisableDirConfig = False, 
                 SPIMode = 'A', SPIClockFactor = 0, CSPINNum = 0, 
                 CLKPinNum = 1, MISOPinNum = 2, MOSIPinNum = 3)
        Args: SPIBytes, A list of bytes to send.
              AutoCS, If True, the CS line is automatically driven low
                      during the SPI communication and brought back high
                      when done.
              DisableDirConfig, If True, function does not set the direction
                                of the line.
              SPIMode, 'A', 'B', 'C',  or 'D'. 
              SPIClockFactor, Sets the frequency of the SPI clock.
              CSPINNum, which pin is CS
              CLKPinNum, which pin is CLK
              MISOPinNum, which pin is MISO
              MOSIPinNum, which pin is MOSI
        Desc: Sends and receives serial data using SPI synchronous
              communication. See Section 5.3.17 of the user's guide.
        """
        if not isinstance(SPIBytes, list):
            raise LabJackException("SPIBytes MUST be a list of bytes")
        
        numSPIBytes = len(SPIBytes)
        
        oddPacket = False
        if numSPIBytes%2 != 0:
            SPIBytes.append(0)
            numSPIBytes = numSPIBytes + 1
            oddPacket = True
        
        command = [ 0 ] * (13 + numSPIBytes)
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 4 + (numSPIBytes/2)
        command[3] = 0x3A
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        
        if AutoCS:
            command[6] |= (1 << 7)
        if DisableDirConfig:
            command[6] |= (1 << 6)
        
        command[6] |= ( self.SPIModes[SPIMode] & 3 )
        
        command[7] = SPIClockFactor
        #command[8] = Reserved
        command[9] = CSPINNum
        command[10] = CLKPinNum
        command[11] = MISOPinNum
        command[12] = MOSIPinNum
        command[13] = numSPIBytes
        if oddPacket:
            command[13] = numSPIBytes - 1
        
        command[14:] = SPIBytes
        
        result = self._writeRead(command, 8+numSPIBytes, [ 0xF8, 1+(numSPIBytes/2), 0x3A ])
        
        return { 'NumSPIBytesTransferred' : result[7], 'SPIBytes' : result[8:] }
    
    def asynchConfig(self, Update = True, UARTEnable = True, DesiredBaud = None, BaudFactor = 63036):
        """
        Name: U6.asynchConfig(Update = True, UARTEnable = True, 
                              DesiredBaud = None, BaudFactor = 63036)
        Args: Update, If True, new values are written.
              UARTEnable, If True, UART will be enabled.
              DesiredBaud, If set, will apply the formualt to 
                           calculate BaudFactor.
              BaudFactor, = 2^16 - 48000000/(2 * Desired Baud). Ignored
                        if DesiredBaud is set.
        Desc: Configures the U6 UART for asynchronous communication. See
              section 5.3.18 of the User's Guide.
        """
        command = [ 0 ] * 10
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x02
        command[3] = 0x14
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        #commmand[6] = 0x00
        if Update:
            command[7] = (1 << 7)
        if UARTEnable:
            command[7] |= (1 << 6)
        
        if DesiredBaud != None:
            BaudFactor = (2**16) - 48000000/(2 * DesiredBaud)   
        
        t = struct.pack("<H", BaudFactor)
        command[8] = ord(t[0])
        command[9] = ord(t[1])
        
    def asynchTX(self, AsynchBytes):
        """
        Name: U6.asynchTX(AsynchBytes)
        Args: AsynchBytes, List of bytes to send
        Desc: Sends bytes to the U6 UART which will be sent asynchronously
              on the transmit line. Section 5.3.20 of the User's Guide.
        """
        
        numBytes = len(AsynchBytes)
        
        oddPacket = False
        if numBytes%2 != 0:
            oddPacket = True
            AsynchBytes.append(0)
            numBytes = numBytes + 1
        
        command = [ 0 ] * (8+numBytes)
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 1 + (numBytes/2)
        command[3] = 0x15
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        #commmand[6] = 0x00
        command[7] = numBytes
        if oddPacket:
            command[7] = numBytes-1
        command[8:] = AsynchBytes
        
        result = self._writeRead(command, 10, [ 0xF8, 0x02, 0x15])
        
        return { 'NumAsynchBytesSent' : result[7], 'NumAsynchBytesInRXBuffer' : result[8] }
    
    def asynchRX(self, Flush = False):
        """
        Name: U6.asynchTX(AsynchBytes)
        Args: Flush, If True, empties the entire 256-byte RX buffer.
        Desc: Sends bytes to the U6 UART which will be sent asynchronously
              on the transmit line. Section 5.3.20 of the User's Guide.
        """
        command = [ 0, 0xF8, 0x01, 0x16, 0, 0, 0, int(Flush)]
        
        result = self._writeRead(command, 40, [ 0xF8, 0x11, 0x16 ])
        
        return { 'NumAsynchBytesInRXBuffer' : result[7], 'AsynchBytes' : result[8:] }
    
    def i2c(self, Address, I2CBytes, EnableClockStretching = False, NoStopWhenRestarting = False, ResetAtStart = False, SpeedAdjust = 0, SDAPinNum = 0, SCLPinNum = 1, numI2CBytesToReceive = 0, AddressByte = None):
        """
        Name: U6.i2c(Address, I2CBytes, EnableClockStretching = False, NoStopWhenRestarting = False, ResetAtStart = False, SpeedAdjust = 0, SDAPinNum = 0, SCLPinNum = 1, NumI2CBytesToReceive = 0, AddressByte = None)
        Args: Address, the address (Not shifted over)
              I2CBytes, a list of bytes to send
              EnableClockStretching, True enables clock streching
              NoStopWhenRestarting, True means no stop sent when restarting
              ResetAtStart, if True, an I2C bus reset will be done
                            before communicating.
              SpeedAdjust, Allows the communication frequency to be reduced.
              SDAPinNum, Which pin will be data
              SCLPinNum, Which pin is clock
              NumI2CBytesToReceive, Number of I2C bytes to expect back.
              AddressByte, The address as you would put it in the lowlevel
                           packet. You don't have to set this.
        Desc: Sends and receives serial data using I2C synchronous
              communication. Section 5.3.21 of the User's Guide.
        """
        numBytes = len(I2CBytes)
        
        oddPacket = False
        if numBytes%2 != 0:
            oddPacket = True
            I2CBytes.append(0)
            numBytes = numBytes+1
        
        command = [ 0 ] * (14+numBytes)
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 4 + (numBytes/2)
        command[3] = 0x3B
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        if EnableClockStretching:
            command[6] = (1 << 4)
        if NoStopWhenRestarting:
            command[6] |= (1 << 2)
        if ResetAtStart:
            command[6] |= (1 << 1)
        
        command[7] = SpeedAdjust
        command[8] = SDAPinNum
        command[9] = SCLPinNum
        
        if AddressByte != None:
            command[10] = AddressByte
        else:
            command[10] = Address << 1
        #command[11] = Reserved
        command[12] = numBytes
        if oddPacket:
            command[12] = numBytes-1
        command[13] = NumI2CBytesToReceive
        command[14:] = I2CBytes
        
        oddResponse = False
        if NumI2CBytesToReceive%2 != 0:
            NumI2CBytesToReceive = NumI2CBytesToReceive+1
            oddResponse = True
        
        result = self._writeRead(command, (12+NumI2CBytesToReceive), [0xF8, (3+(NumI2CBytesToReceive/2)), 0x3B])
        
        if NumI2CBytesToReceive != 0:
            return { 'AckArray' : result[8:12], 'I2CBytes' : result[12:] }
        else:
            return { 'AckArray' : result[8:12] }
            
    def sht1x(self, DataPinNum = 0, ClockPinNum = 1, SHTOptions = 0xc0):
        """
        Name: U6.sht1x(DataPinNum = 0, ClockPinNum = 1, SHTOptions = 0xc0)
        Args: DataPinNum, Which pin is the Data line
              ClockPinNum, Which line is the Clock line
        SHTOptions (and proof people read documentation):
            bit 7 = Read Temperature
            bit 6 = Read Realtive Humidity
            bit 2 = Heater. 1 = on, 0 = off
            bit 1 = Reserved at 0
            bit 0 = Resolution. 1 = 8 bit RH, 12 bit T; 0 = 12 RH, 14 bit T
        Desc: Reads temperature and humidity from a Sensirion SHT1X sensor.
              Section 5.3.22 of the User's Guide.
        """
        command = [ 0 ] * 10
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x02
        command[3] = 0x39
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        command[6] = DataPinNum
        command[7] = ClockPinNum
        #command[8] = Reserved
        command[9] = SHTOptions
        
        result = self._writeRead(command, 16, [ 0xF8, 0x05, 0x39])
        
        val = (result[11]*256) + result[10]
        temp = -39.60 + 0.01*val
        
        val = (result[14]*256) + result[13]
        humid = -4 + 0.0405*val + -.0000028*(val*val)
        humid = (temp - 25)*(0.01 + 0.00008*val) + humid
        
        return { 'StatusReg' : result[8], 'StatusCRC' : result[9], 'Temperature' : temp, 'TemperatureCRC' : result[12], 'Humidity' : humid, 'HumidityCRC' : result[15] }
            
    # --------------------------- Old U6 code -------------------------------

    def _readCalDataBlock(self, n):
        """
        Internal routine to read the specified calibration block (0-2)
        """ 
        sendBuffer = [0] * 8
        sendBuffer[1] = 0xF8  # command byte
        sendBuffer[2] = 0x01  #  number of data words
        sendBuffer[3] = 0x2D  #  extended command number
        sendBuffer[6] = 0x00
        sendBuffer[7] = n     # Blocknum = 0
        self.write(sendBuffer)
        buff = self.read(40)
        return buff[8:]

    def getCalibrationData(self):
        """
        Name: getCalibrationData(self)
        Args: None
        Desc: Gets the slopes and offsets for AIN and DACs,
              as well as other calibration data
        
        >>> myU3 = U6()
        >>> myU3.openU6()
        >>> myU3.getCalibrationData()
        >>> myU3.calInfo
        <ainDiffOffset: -2.46886488446,...>
        """
        if self.debug is True:
            print "Calibration data retrieval"
        
        #reading block 0 from memory
        rcvBuffer = self._readCalDataBlock(0)
        
        # Positive Channel calibration
        self.calInfo.ain10vSlope = toDouble(rcvBuffer[:8])
        self.calInfo.ain10vOffset = toDouble(rcvBuffer[8:16])    
        self.calInfo.ain1vSlope = toDouble(rcvBuffer[16:24])
        self.calInfo.ain1vOffset = toDouble(rcvBuffer[24:])
        
        #reading block 1 from memory
        rcvBuffer = self._readCalDataBlock(1)
        
        self.calInfo.ain100mvSlope = toDouble(rcvBuffer[:8])
        self.calInfo.ain100mvOffset = toDouble(rcvBuffer[8:16])
        self.calInfo.ain10mvSlope = toDouble(rcvBuffer[16:24])
        self.calInfo.ain10mvOffset = toDouble(rcvBuffer[24:])
        
        self.calInfo.ainSlope = [self.calInfo.ain10vSlope, self.calInfo.ain1vSlope, self.calInfo.ain100mvSlope, self.calInfo.ain10mvSlope]
        self.calInfo.ainOffset = [ self.calInfo.ain10vOffset, self.calInfo.ain1vOffset, self.calInfo.ain100mvOffset, self.calInfo.ain10mvOffset ]
        
        #reading block 2 from memory
        rcvBuffer = self._readCalDataBlock(2)
        
        # Negative Channel calibration
        self.calInfo.ain10vNegSlope = toDouble(rcvBuffer[:8])
        self.calInfo.ain10vCenter = toDouble(rcvBuffer[8:16])
        self.calInfo.ain1vNegSlope = toDouble(rcvBuffer[16:24])
        self.calInfo.ain1vCenter = toDouble(rcvBuffer[24:])
        
        #reading block 3 from memory
        rcvBuffer = self._readCalDataBlock(3)
        
        self.calInfo.ain100mvNegSlope = toDouble(rcvBuffer[:8])
        self.calInfo.ain100mvCenter = toDouble(rcvBuffer[8:16])
        self.calInfo.ain10mvNegSlope = toDouble(rcvBuffer[16:24])
        self.calInfo.ain10mvCenter = toDouble(rcvBuffer[24:])
        
        self.calInfo.ainNegSlope = [ self.calInfo.ain10vNegSlope, self.calInfo.ain1vNegSlope, self.calInfo.ain100mvNegSlope, self.calInfo.ain10mvNegSlope ]
        self.calInfo.ainCenter = [ self.calInfo.ain10vCenter, self.calInfo.ain1vCenter, self.calInfo.ain100mvCenter, self.calInfo.ain10mvCenter ]
        
        #reading block 4 from memory
        rcvBuffer = self._readCalDataBlock(4)
        
        # Miscellaneous
        self.calInfo.dac0Slope = toDouble(rcvBuffer[:8])
        self.calInfo.dac0Offset = toDouble(rcvBuffer[8:16])
        self.calInfo.dac1Slope = toDouble(rcvBuffer[16:24])
        self.calInfo.dac1Offset = toDouble(rcvBuffer[24:])
        
        #reading block 5 from memory
        rcvBuffer = self._readCalDataBlock(5)
        
        self.calInfo.currentOutput0 = toDouble(rcvBuffer[:8])
        self.calInfo.currentOutput1 = toDouble(rcvBuffer[8:16])
        
        self.calInfo.temperatureSlope = toDouble(rcvBuffer[16:24])
        self.calInfo.temperatureOffset = toDouble(rcvBuffer[24:])
        
        if self.productName == "U6-Pro":
            # Hi-Res ADC stuff
            
            #reading block 6 from memory
            rcvBuffer = self._readCalDataBlock(6)
            
            # Positive Channel calibration
            self.calInfo.proAin10vSlope = toDouble(rcvBuffer[:8])
            self.calInfo.proAin10vOffset = toDouble(rcvBuffer[8:16])
            self.calInfo.proAin1vSlope = toDouble(rcvBuffer[16:24])
            self.calInfo.proAin1vOffset = toDouble(rcvBuffer[24:])
            
            #reading block 7 from memory
            rcvBuffer = self._readCalDataBlock(7)
            
            self.calInfo.proAin100mvSlope = toDouble(rcvBuffer[:8])
            self.calInfo.proAin100mvOffset = toDouble(rcvBuffer[8:16])
            self.calInfo.proAin10mvSlope = toDouble(rcvBuffer[16:24])
            self.calInfo.proAin10mvOffset = toDouble(rcvBuffer[24:])
            
            self.calInfo.proAinSlope = [self.calInfo.proAin10vSlope, self.calInfo.proAin1vSlope, self.calInfo.proAin100mvSlope, self.calInfo.proAin10mvSlope]
            self.calInfo.proAinOffset = [ self.calInfo.proAin10vOffset, self.calInfo.proAin1vOffset, self.calInfo.proAin100mvOffset, self.calInfo.proAin10mvOffset ]
            
            #reading block 8 from memory
            rcvBuffer = self._readCalDataBlock(8)
            
            # Negative Channel calibration
            self.calInfo.proAin10vNegSlope = toDouble(rcvBuffer[:8])
            self.calInfo.proAin10vCenter = toDouble(rcvBuffer[8:16])
            self.calInfo.proAin1vNegSlope = toDouble(rcvBuffer[16:24])
            self.calInfo.proAin1vCenter = toDouble(rcvBuffer[24:])
            
            #reading block 9 from memory
            rcvBuffer = self._readCalDataBlock(9)
            
            self.calInfo.proAin100mvNegSlope = toDouble(rcvBuffer[:8])
            self.calInfo.proAin100mvCenter = toDouble(rcvBuffer[8:16])
            self.calInfo.proAin10mvNegSlope = toDouble(rcvBuffer[16:24])
            self.calInfo.proAin10mvCenter = toDouble(rcvBuffer[24:])
        
            self.calInfo.proAinNegSlope = [ self.calInfo.proAin10vNegSlope, self.calInfo.proAin1vNegSlope, self.calInfo.proAin100mvNegSlope, self.calInfo.proAin10mvNegSlope ]
            self.calInfo.proAinCenter = [ self.calInfo.proAin10vCenter, self.calInfo.proAin1vCenter, self.calInfo.proAin100mvCenter, self.calInfo.proAin10mvCenter ]

    def binaryToCalibratedAnalogVoltage(self, gainIndex, bytesVoltage, is16Bits=False):
        """
        Name: binaryToCalibratedAnalogVoltage(gainIndex, bytesVoltage, is16Bits = False)
        Args: gainIndex, which gain did you use?
              bytesVoltage, bytes returned from the U6
              is16bits, set to True if bytesVolotage is 16 bits (not 24)
        Desc: Converts binary voltage to an analog value.
        
        """
        if not is16Bits:
            bits = float(bytesVoltage)/256
        else:
            bits = float(bytesVoltage)
        
        center = self.calInfo.ainCenter[gainIndex]
        negSlope = self.calInfo.ainNegSlope[gainIndex]
        posSlope = self.calInfo.ainSlope[gainIndex]
        
        if self.productName == "U6-Pro":
            center = self.calInfo.proAinCenter[gainIndex]
            negSlope = self.calInfo.proAinNegSlope[gainIndex]
            posSlope = self.calInfo.proAinSlope[gainIndex]
        
        if bits < center:
            return (center - bits) * negSlope
        else:
            return (bits - center) * posSlope
            
            
    
    def binaryToCalibratedAnalogTemperature(self, bytesTemperature):
        voltage = self.binaryToCalibratedAnalogVoltage(0, bytesTemperature)
        return self.calInfo.temperatureSlope * float(voltage) + self.calInfo.temperatureOffset
        
    def softReset(self):
        """
        Name: softReset
        Args: none
        Desc: Send a soft reset.
        
        >>> myU6 = U6()
        >>> myU6.openU6()
        >>> myU6.softReset()
        """
        self.Write([ 0x00, 0x99, 0x00, 0x00 ])
        self.Read(4)
        
    def hardReset(self):
        """
        Name: hardReset
        Args: none
        Desc: Send a hard reset.
        
        >>> myU6 = U6()
        >>> myU6.openU6()
        >>> myU6.hardReset()
        """
        self.Write([ 0x00, 0x99, 0x01, 0x00])
        self.Read(4)

    def setLED(self, state):
        """
        Name: setLED(self, state)
        Args: state: 1 = On, 0 = Off
        Desc: Sets the state of the LED. (5.2.5.4 of user's guide)
        
        >>> myU6 = U6()
        >>> myU6.openU6()
        >>> myU6.setLED(0)
        ... (LED turns off) ...
        """
        self.getFeedback(LED(state))

    def getTemperature(self):
        """
        Name: getTemperature
        Args: none
        Desc: Reads the U3's internal temperature sensor in Kelvin.  See Section 2.6.4 of the U3 User's Guide.
        
        >>> myU6.getTemperature()
        299.87723471224308
        """
        result = self.getFeedback(AIN24AR(14))
        return self.binaryToCalibratedAnalogTemperature(result[0]['AIN'])
        
    def getAIN(self, positiveChannel, resolutionIndex = 0, gainIndex = 15, settlingFactor = 0, differential = False):
        """
        Name: getAIN
        Args: positiveChannel, resolutionIndex = 0, gainIndex = 15, settlingFactor = 0, differential = False
        Desc: Reads an AIN can applies the calibration constants to it.
        
        >>> myU6.getAIN(14)
        299.87723471224308
        """
        result = self.getFeedback(AIN24AR(positiveChannel, resolutionIndex, gainIndex, settlingFactor, differential))
        
        return self.binaryToCalibratedAnalogVoltage(result[0]['GainIndex'], result[0]['AIN'])


class FeedbackCommand(object):
    '''
    The base FeedbackCommand class
    
    Used to make Feedback easy. Make a list of these
    and call getFeedback.
    '''
    readLen = 0
    def handle(self, input):
        return None

validChannels = range(144)
class AIN(FeedbackCommand):
    '''
    Analog Input Feedback command

    AIN(PositiveChannel)
    
    PositiveChannel : the positive channel to use 

    NOTE: This function kept for compatibility. Please use
          the new AIN24 and AIN24AR.
    
    returns 16-bit unsigned int sample
    '''
    def __init__(self, PositiveChannel):
        if PositiveChannel not in validChannels:
            raise LabJackException("Invalid Positive Channel specified")
        
        self.cmdBytes = [ 0x01, PositiveChannel, 0 ]

    readLen =  2

    def handle(self, input):
        result = (input[1] << 8) + input[0]
        return result

class AIN24(FeedbackCommand):
    '''
    Analog Input 24-bit Feedback command

    ainCommand = AIN24(PositiveChannel, ResolutionIndex = 0, GainIndex = 0, SettlingFactor = 0, Differential = False)
    
    See section 5.2.5.2 of the user's guide.
    
    NOTE: If you use a gain index of 15 (autorange), you should be using
          the AIN24AR command instead. 
    
    positiveChannel : The positive channel to use
    resolutionIndex : 0=default, 1-8 for high-speed ADC, 
                      9-13 for high-res ADC on U6-Pro.
    gainIndex : 0=x1, 1=x10, 2=x100, 3=x1000, 15=autorange
    settlingFactor : 0=5us, 1=10us, 2=100us, 3=1ms, 4=10ms
    differential : If this bit is set, a differential reading is done where
                   the negative channel is positiveChannel+1
    

    returns 24-bit unsigned int sample
    '''
    def __init__(self, PositiveChannel, ResolutionIndex = 0, GainIndex = 0, SettlingFactor = 0, Differential = False):
        if PositiveChannel not in validChannels:
            raise LabJackException("Invalid Positive Channel specified")

        byte2 = ( ResolutionIndex & 0xf )
        byte2 = ( ( GainIndex & 0xf ) << 4 ) + byte2
        
        byte3 = (int(Differential) << 8) + SettlingFactor
        self.cmdBytes = [ 0x02, PositiveChannel, byte2, byte3 ]

    readLen =  3

    def handle(self, input):
        #Put it all into an integer.
        result = (input[2] << 16 ) + (input[1] << 8 ) + input[0]
        return result

class AIN24AR(FeedbackCommand):
    '''
    Autorange Analog Input 24-bit Feedback command

    ainARCommand = AIN24AR(0, ResolutionIndex = 0, GainIndex = 15, SettlingFactor = 0, Differential = False)
    
    See section 5.2.5.3 of the user's guide
    
    PositiveChannel : The positive channel to use
    ResolutionIndex : 0=default, 1-8 for high-speed ADC, 
                      9-13 for high-res ADC on U6-Pro.
    GainIndex : 0=x1, 1=x10, 2=x100, 3=x1000, 15=autorange
    SettlingFactor : 0=5us, 1=10us, 2=100us, 3=1ms, 4=10ms
    Differential : If this bit is set, a differential reading is done where
                   the negative channel is positiveChannel+1

    returns a dictionary:
        { 
        'value' : < 24-bit binary reading >, 
        'resolutionIndex' : < actual resolution setting used for the reading >,
        'gainIndex' : < actual gain used for the reading >,
        'status' : < reserved for future use >
        }
    '''
    def __init__(self, PositiveChannel, ResolutionIndex = 0, GainIndex = 15, SettlingFactor = 0, Differential = False):
        if PositiveChannel not in validChannels:
            raise LabJackException("Invalid Positive Channel specified")

        byte2 = ( ResolutionIndex & 0xf )
        byte2 = ( ( GainIndex & 0xf ) << 4 ) + byte2
        
        byte3 = (int(Differential) << 8) + SettlingFactor
        self.cmdBytes = [ 0x03, PositiveChannel, byte2, byte3 ]

    readLen =  5

    def handle(self, input):
        #Put it all into an integer.
        result = (input[2] << 16 ) + (input[1] << 8 ) + input[0]
        resolutionIndex = input[3] & 0xf
        gainIndex = ( input[3] >> 4 ) & 0xf 
        status = input[4]
        
        return { 'AIN' : result, 'ResolutionIndex' : resolutionIndex, 'GainIndex' : gainIndex, 'Status' : status }   

class WaitShort(FeedbackCommand):
    '''
    WaitShort Feedback command

    specify the number of 128us time increments to wait
    '''
    def __init__(self, Time):
        self.cmdBytes = [ 5, Time % 256 ]

class WaitLong(FeedbackCommand):
    '''
    WaitLong Feedback command
    
    specify the number of 32ms time increments to wait
    '''
    def __init__(self, Time):
        self.cmdBytes = [ 6, Time % 256 ]

class LED(FeedbackCommand):
    '''
    LED Toggle

    specify whether the LED should be on or off by truth value
    '''
    def __init__(self, State):
        self.cmdBytes = [ 9, int(bool(State)) ]

class BitStateRead(FeedbackCommand):
    '''
    BitStateRead Feedback command

    read the state of a single bit of digital I/O.  Only digital
    lines return valid readings.

    IONumber: 0-7=FIO, 8-15=EIO, 16-19=CIO
    return 0 or 1
    '''
    def __init__(self, IONumber):
        self.cmdBytes = [ 10, IONumber % 20 ]

    readLen = 1

    def handle(self, input):
        return int(bool(input[0]))

class BitStateWrite(FeedbackCommand):
    '''
    BitStateWrite Feedback command

    write a single bit of digital I/O.  The direction of the 
    specified line is forced to output.

    IONumber: 0-7=FIO, 8-15=EIO, 16-19=CIO
    State: 0 or 1
    '''
    def __init__(self, IONumber, State):
        self.cmdBytes = [ 11, (IONumber % 20) + (int(bool(State)) << 7) ]

class BitDirRead(FeedbackCommand):
    '''
    Read the digital direction of one I/O

    IONumber: 0-7=FIO, 8-15=EIO, 16-19=CIO
    returns 1 = Output, 0 = Input
    '''
    def __init__(self, IONumber):
        self.cmdBytes = [ 12, IONumber % 20 ]

    readLen = 1

    def handle(self, input):
        return int(bool(input[0]))

class BitDirWrite(FeedbackCommand):
    '''
    BitDirWrite Feedback command

    Set the digital directino of one I/O

    IONumber: 0-7=FIO, 8-15=EIO, 16-19=CIO
    Direction: 1 = Output, 0 = Input
    '''
    def __init__(self, IONumber, Direction):
        self.cmdBytes = [ 13, (IONumber % 20) + (int(bool(Direction)) << 7) ]

class PortStateRead(FeedbackCommand):
    """
    PortStateRead Feedback command
    Reads the state of all digital I/O.
    """
    def __init__(self):
        self.cmdBytes = [ 26 ]
        
    readLen = 3
    
    def handle(self, input):
        return {'FIO' : input[0], 'EIO' : input[1], 'CIO' : input[2] }

class PortStateWrite(FeedbackCommand):
    """
    PortStateWrite Feedback command
    
    state: A list of 3 bytes representing FIO, EIO, CIO
    WriteMask: A list of 3 bytes, representing which to update. Default is all ones.
    """
    def __init__(self, State, WriteMask = [ 0xff, 0xff, 0xff]):
        self.cmdBytes = [ 27 ] + WriteMask + State
        
class PortDirRead(FeedbackCommand):
    """
    PortDirRead Feedback command
    Reads the direction of all digital I/O.
    """
    def __init__(self):
        self.cmdBytes = [ 28 ]
        
    readLen = 3
    
    def handle(self, input):
        return {'FIO' : input[0], 'EIO' : input[1], 'CIO' : input[2] }

class PortDirWrite(FeedbackCommand):
    """
    PortDirWrite Feedback command
    
    Direction: A list of 3 bytes representing FIO, EIO, CIO
    WriteMask: A list of 3 bytes, representing which to update. Default is all ones.
    """
    def __init__(self, Direction, WriteMask = [ 0xff, 0xff, 0xff]):
        self.cmdBytes = [ 29 ] + WriteMask + Direction
    
class DAC8(FeedbackCommand):
    '''
    8-bit DAC Feedback command
    
    Controls a single analog output

    dac: 0 or 1
    value: 0-255
    '''
    def __init__(self, dac, value):
        self.cmdBytes = [ 34 + (dac % 2), value % 256 ]
        
class DAC0_8(DAC8):
    def __init__(self, Value):
        DAC8.__init__(self, 0, Value)

class DAC1_8(DAC8):
    def __init__(self, Value):
        DAC8.__init__(self, 1, Value)

class DAC16(FeedbackCommand):
    '''
    16-bit DAC Feedback command

    Controls a single analog output

    dac: 0 or 1
    value: 0-65535
    '''
    def __init__(self, dac, value):
        self.cmdBytes = [ 38 + (dac % 2), value % 256, value >> 8 ]

class DAC0_16(DAC16):
    def __init__(self, Value):
        DAC16.__init__(self, 0, Value)

class DAC1_16(DAC16):
    def __init__(self, Value):
        DAC16.__init__(self, 1, Value)
        
class Timer(FeedbackCommand):
    """
    For reading the value of the Time. It provides the ability to update/reset a given timer, and read the timer value. ( p. 104 of the User's Guide)
    
    >>> timerRead = Timer(timer, updateReset, value)
    
    timer: Either 0 or 1 for counter0 or counter1
     
    updateReset: Set True if you want to update the value
    
    value: Only updated if the UpdateReset bit is 1.  The meaning of this 
parameter varies with the timer mode.
    
    """
    def __init__(self, timer, updateReset = False, value=0):
        if timer != 0 and timer != 1:
            raise LabJackException("Timer should be either 0 or 1.")
        if updateReset and value == None:
            raise LabJackException("UpdateReset set but no value.")
            
        
        self.cmdBytes = [ (42 + (2*timer)), updateReset, value % 256, value >> 8 ]
    
    readLen = 4
    
    def handle(self, input):
        inStr = ''.join([chr(x) for x in input])
        return struct.unpack('<I', inStr )

class Timer0(Timer):
    def __init__(self, UpdateReset = False, Value = 0):
        Timer.__init__(self, 0, UpdateReset, Value)

class Timer1(Timer):
    def __init__(self, UpdateReset = False, Value = 0):
        Timer.__init__(self, 1, UpdateReset, Value)

class TimerConfig(FeedbackCommand):
    def __init__(self, timer, mode, value=0):
        '''Creates command bytes for configureing a Timer'''
        #Conditions come from pages 33-34 of user's guide
        if timer != 0 and timer != 1:
            raise LabJackException("Timer should be either 0 or 1.")
            
        if value < 4:
            raise LabJackException("Value should be greater than 3.")
        
        if mode > 13 or mode < 0:
            raise LabJackException("Invalid Timer Mode.")
        
        self.cmdBytes = [43 + (timer * 2), mode, value % 256, value >> 8]

class Timer0Config(TimerConfig):
    def __init__(self, TimerMode, Value = 0):
        TimerConfig.__init__(self, 0, TimerMode, Value)

class Timer1Config(TimerConfig):
    def __init__(self, TimerMode, Value = 0):
        TimerConfig.__init__(self, 1, TimerMode, Value)

class Counter(FeedbackCommand):
    '''
    Counter Feedback command

    Reads a hardware counter, optionally resetting it

    counter: 0 or 1
    reset: truth value

    Returns the current count from the counter if enabled.  If reset,
    this is the value before the reset.
    '''
    def __init__(self, counter, reset):
        self.cmdBytes = [ 54 + (counter % 2), int(bool(reset))]

    readLen = 4

    def handle(self, input):
        inStr = ''.join([chr(x) for x in input])
        return struct.unpack('<I', inStr )

class Counter0(Counter):
    def __init__(self, Reset = False):
        Counter.__init__(self, 0, Reset)

class Counter1(Counter):
    def __init__(self, Reset = False):
        Counter.__init__(self, 1, Reset)