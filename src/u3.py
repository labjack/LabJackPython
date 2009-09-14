"""
Name: u3.py
Desc: Defines a much better U3 class.
"""
from LabJackPython import *
import struct

class U3(Device):
    """
    U3 Class for all U3 specific low-level commands.
    
    u3 = U3()
    u3.open()
    
    """
    def __init__(self, handle = None, localId = None, serialNumber = None):
        self.handle = handle
        self.localId = localId
        self.serialNumber = serialNumber
        self.devType = 3
        self.debug = False
        self.streamConfiged = False
        self.streamStarted = False
        
    def open(self, firstFound = True, localId = None, devNumber = None, handleOnly = False):
        """
        Name: U3.open(firstFound = True, localId = None, devNumber = None,
                      handleOnly = False)
        Args: firstFound, will open the first U3 found.
              localId, the localID of the U3 you wish to open
              devNumber, firstFound is devNumber = 1, devNumber = 2 is second
                         found.
              handleOnly, if True, it won't read anything about the U3 just 
                          get the device handle.
        Desc: Use to open a U3.
        """
        Device.open(self, 3, firstFound = firstFound, localId = localId, devNumber = devNumber, handleOnly = handleOnly )
    
    def configU3(self, LocalID = None, TimerCounterConfig = None, FIOAnalog = None, FIODirection = None, FIOState = None, EIOAnalog = None, EIODirection = None, EIOState = None, CIODirection = None, CIOState = None, DAC1Enable = None, DAC0 = None, DAC1 = None, TimerClockConfig = None, TimerClockDivisor = None, CompatibilityOptions = None ):
        """
        Name: U3.configU3(LocalID = None, TimerCounterConfig = None, FIOAnalog = None, FIODirection = None, FIOState = None, EIOAnalog = None, EIODirection = None, EIOState = None, CIODirection = None, CIOState = None, DAC1Enable = None, DAC0 = None, DAC1 = None, TimerClockConfig = None, TimerClockDivisor = None, CompatibilityOptions = None)
        Args: See section 5.2.2 of the users guide.
        Desc: Sends the low-level configU3 command.
        """
        
        writeMask = 0
        
        if FIOAnalog is not None or FIODirection is not None or FIOState is not None or EIOAnalog is not None or EIODirection is not None or EIOState is not None or CIODirection is not None or CIOState is not None:
            writeMask |= 2
        
        if DAC1Enable is not None or DAC0 is not None or DAC1 is not None:
            writeMask |= 4
            
        if LocalID is not None:
            writeMask |= 8
        
        command = [ 0 ] * 26
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x0A
        command[3] = 0x08
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        command[6] = writeMask
        #command[7] = WriteMask1
        
        if LocalID is not None:
            command[8] = LocalID
        
        if TimerCounterConfig is not None:
            command[9] = TimerCounterConfig
        
        if FIOAnalog is not None:
            command[10] = FIOAnalog
        
        if FIODirection is not None:
            command[11] = FIODirection
        
        if FIOState is not None:
            command[12] = FIOState
        
        if EIOAnalog is not None:
            command[13] = EIOAnalog
        
        if EIODirection is not None:
            command[14] = EIODirection
        
        if EIOState is not None:
            command[15] = EIOState
        
        if CIODirection is not None:
            command[16] = CIODirection
        
        if CIOState is not None:
            command[17] = CIOState
        
        if DAC1Enable is not None:
            command[18] = DAC1Enable
            
        if DAC0 is not None:
            command[19] = DAC0
            
        if DAC1 is not None:
            command[20] = DAC1
            
        if TimerClockConfig is not None:
            command[21] = TimerClockConfig
            
        if TimerClockDivisor is not None:
            command[22] = TimerClockDivisor
            
        if CompatibilityOptions is not None:
            command[23] = CompatibilityOptions
        
        
        result = self._writeRead(command, 38, [0xF8, 0x10, 0x08])
        
        # Error-free, time to parse the response
        self.firmwareVersion = "%d.%d" % (result[10], result[9])
        self.bootloaderVersion = "%d.%d" % (result[12], result[11])
        self.hardwareVersion = "%d.%d" % (result[14], result[13])
        self.serialNumber = struct.unpack("<I", struct.pack(">BBBB", *result[15:19]))[0]
        self.productId = struct.unpack("<H", struct.pack(">BB", *result[19:21]))[0]
        self.localId = result[21]
        self.timerCounterMask = result[22]
        self.fioAnalog = result[23]
        self.fioDirection = result[24]
        self.fioState = result[25]
        self.eioAnalog = result[26]
        self.eioDirection = result[27]
        self.eioState = result[28]
        self.cioDirection = result[29]
        self.cioState = result[30]
        self.dac1Enable = result[31]
        self.dac0 = result[32]
        self.dac1 = result[33]
        self.timerClockConfig = result[34]
        self.timerClockDivisor = result[35]
        if result[35] == 0:
            self.timerClockDivisor = 256
        
        self.compatibilityOptions = result[36]
        self.versionInfo = result[37]
        self.deviceName = 'U3'
        if self.versionInfo == 1:
            self.deviceName += 'B'
        elif self.versionInfo == 2:
            self.deviceName += '-LV'
        elif self.versionInfo == 18:
            self.deviceName += '-HV'
        
        return { 'FirmwareVersion' : self.firmwareVersion, 'BootloaderVersion' : self.bootloaderVersion, 'HardwareVersion' : self.hardwareVersion, 'SerialNumber' : self.serialNumber, 'ProductID' : self.productId, 'LocalID' : self.localId, 'TimerCounterMask' : self.timerCounterMask, 'FIOAnalog' : self.fioAnalog, 'FIODirection' : self.fioDirection, 'FIOState' : self.fioState, 'EIOAnalog' : self.eioAnalog, 'EIODirection' : self.eioDirection, 'EIOState' : self.eioState, 'CIODirection' : self.cioDirection, 'CIOState' : self.cioState, 'DAC1Enable' : self.dac1Enable, 'DAC0' : self.dac0, 'DAC1' : self.dac1, 'TimerClockConfig' : self.timerClockConfig, 'TimerClockDivisor' : self.timerClockDivisor, 'CompatibilityOptions' : self.compatibilityOptions, 'VersionInfo' : self.versionInfo, 'DeviceName' : self.deviceName }

    def configIO(self, TimerCounterPinOffset = 4, EnableCounter1 = None, EnableCounter0 = None, NumberOfTimersEnabled = None, FIOAnalog = None, EIOAnalog = None, EnableUART = None):
        """
        Name: U3.configIO(TimerCounterPinOffset = 4, EnableCounter1 = None, EnableCounter0 = None, NumberOfTimersEnabled = None, FIOAnalog = None, EIOAnalog = None, EnableUART = None)
        Args: See section 5.2.3 of the user's guide.
        Desc: The configIO command.
        """
        
        writeMask = 0
        
        if EIOAnalog is not None:
            writeMask |= 1
            writeMask |= 8
        
        if FIOAnalog is not None:
            writeMask |= 1
            writeMask |= 4
            
        if EnableUART is not None:
            writeMask |= 1
            writeMask |= (1 << 5)
            
        if TimerCounterPinOffset is not None or EnableCounter1 is not None or EnableCounter0 is not None or NumberOfTimersEnabled is not None :
            writeMask |= 1
        
        command = [ 0 ] * 12
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x03
        command[3] = 0x0B
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        command[6] = writeMask
        #command[7] = Reserved
        command[8] = 0
        
        if EnableUART is not None:
            command[9] = int(EnableUART) << 2
            if TimerCounterPinOffset is None:
                TimerCounterPinOffset = 4
            
        
        if TimerCounterPinOffset is not None:
            command[8] |= ( TimerCounterPinOffset & 15 ) << 4
        if EnableCounter1 is not None:
            command[8] |= 1 << 3
        if EnableCounter0 is not None:
            command[8] |= 1 << 2
        if NumberOfTimersEnabled is not None:
            command[8] |= ( NumberOfTimersEnabled & 3 )
            
        if FIOAnalog is not None:
            command[10] = FIOAnalog
        
        if EIOAnalog is not None:
            command[11] = EIOAnalog
        
        result = self._writeRead(command, 12, [0xF8, 0x03, 0x0B])
        
        self.timerCounterConfig = result[8]
        self.dac1Enable = result[9]
        self.fioAnalog = result[10]
        self.eioAnalog = result[11]
        
        return { 'TimerCounterConfig' : self.timerCounterConfig, 'DAC1Enable' : self.dac1Enable, 'FIOAnalog' : self.fioAnalog, 'EIOAnalog' : self.eioAnalog }
    
    def configTimerClock(self, TimerClockBase = None, TimerClockDivisor = None):
        """
        Name: U3.configTimerClock(TimerClockBase = None, TimerClockDivisor = None)
        Args: TimeClockBase, the base for the timer clock.
              TimerClockDivisor, the divisor for the clock.
        
        Desc: Writes and reads the time clock configuration. See section 5.2.4
              of the user's guide.
        
        Note: TimerClockBase and TimerClockDivisor must be set at the same time.
        """
        command = [ 0 ] * 10
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x02
        command[3] = 0x0A
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        #command[6] = Reserved
        #command[7] = Reserved
        if TimerClockBase is not None:
            command[8] = ( 1 << 7 ) + ( TimerClockBase & 7 )
            if TimerClockDivisor is not None:
                command[9] =  TimerClockDivisor
        if TimerClockDivisor is not None:
            raise LabJackException("You can't set just the divisor, must set both.")
        
        result = self._writeRead(command, 10, [0xf8, 0x02, 0x0A])
        
        self.timerClockBase = ( result[8] & 7 )
        self.timerClockDivisor = result[9]
        
        return { 'TimerClockBase' : self.timerClockBase, 'TimerClockDivisor' : self.timerClockDivisor }

    def setFIOState(self, fioNum, state = 1):
        """
        Name: U3.setFIOState(fioNum, state = 1)
        Args: fioNum, which FIO to change
              state, 1 = High, 0 = Low
        Desc: A convenience function to set the state of an FIO. Will also 
              set the direction to output.
        
        """
        self.getFeedback(BitDirWrite(fioNum, 1), BitStateWrite(fioNum, state))
    
    def getFIOState(self, fioNum):
        """
        Name: U3.getFIOState(fioNum)
        Args: fioNum, which FIO to read
        Desc: A convenience function to read the state of an FIO. Unpredictable
              results if the pin is not set to output.
        
        """
        return self.getFeedback(BitStateRead(fioNum))[0]
    
    def getAIN(self, posChannel, negChannel = 31, longSettle=False, quickSample=False):
        """
        Name: U3.getAIN(posChannel, negChannel = 31, longSettle=False,
                                                     quickSample=False)
        Args: posChannel, the positive channel to read from.
              negChannel, the negitive channel to read from.
              longSettle, set to True for longSettle
              quickSample, set to True for quickSample
        Desc: A convenience function to read an AIN. 
        
        TODO: Apply conversions.
        """
        return self.getFeedback(AIN(posChannel, negChannel, longSettle, quickSample))[0]

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
        Name: U3.getFeedback(commandlist)
        Args: the FeedbackCommands to run
        Desc: Forms the commandlist into a packet, sends it to the U3, and reads the response.
        
        >>> myU3 = U3()
        >>> myU3.open()
        >>> ledCommand = U3.LED(False)
        >>> internalTempCommand = U3.AIN(30, 31, True)
        >>> myU3.getFeedback(ledCommand, internalTempCommand)
        [None, 23200]

        OR if you like the list version better:
        
        >>> myU3 = U3()
        >>> myU3.open()
        >>> ledCommand = U3.LED(False)
        >>> internalTempCommand = U3.AIN(30, 31, True)
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
        
        if self.debug: print "Result: ", rcvBuffer
        
        # Check the response for errors
        if rcvBuffer[1] != 0xF8 or rcvBuffer[3] != 0x00:
            raise LabJackException("Got incorrect command bytes")
        elif not verifyChecksum(rcvBuffer):
            raise LabJackException("Checksum was incorrect")
        elif rcvBuffer[6] != 0:
            raise LabJackException("Got error number %d from labjack" % rcvBuffer[6])
        
        results = []
        i = 9
        return self._buildFeedbackResults(rcvBuffer, commandlist, results, i)
        
    def readMem(self, blockNum, readCal=False):
        """
        Name: U3.readMem(blockNum, readCal=False)
        Args: blockNum, which block to read from
              readCal, set to True to read from calibration instead.
        Desc: Reads 1 block (32 bytes) from the non-volatile user or calibration
              memory. Please read section 5.2.6 of the user's guide before you
              do something you may regret.
        
        NOTE: Do not call this function while streaming.
        """
        command = [ 0 ] * 8
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x01
        command[3] = 0x2A
        if readCal:
            command[3] = 0x2D
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        command[6] = 0x00
        command[7] = blockNum
        
        result = self._writeRead(command, 40, [0xF8, 0x11, command[3]])
        
        return result[8:]
        
    def readCal(self, blockNum):
        """
        Name: U3.readCal(blockNum)
        Args: blockNum, which blog to read
        Desc: See the description of readMem and section 5.2.6 of the user's
              guide.
        Note: Do not call this function while streaming.
        """
        return self.readMem(blockNum, readCal = True)
        
    def writeMem(self, blockNum, data, writeCal=False):
        """
        Name: U3.writeMem(blockNum, data, writeCal=False)
        Args: blockNum, which block to write
              data, a list of bytes to write.
              writeCal, set to True to write to calibration instead
        Desc: Writes 1 block (32 bytes) from the non-volatile user or
              calibration memory. Please read section 5.2.7 of the user's guide
              before you do something you may regret. Memory must be erased
              before writing.
        
        Note: Do not call this function while streaming.
        """
        if not isinstance(data, list):
            raise LabJackException("Data must be a list of bytes")
        
        command = [ 0 ] * 40
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x11
        command[3] = 0x28
        if writeCal:
            command[3] = 0x2B
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        command[6] = 0x00
        command[7] = blockNum
        command[8:] = data
        
        
        self._writeRead(command, 8, [0xF8, 0x01, command[3]])
    
    def writeCal(self, blockNum):
        """
        Name: U3.writeCal(blockNum, data)
        Args: blockNum, which block to write
              data, a list of bytes
        Desc: See the description of writeMem and section 5.2.7 of the user's
              guide.
        Note: Do not call this function while streaming.
        """
        return self.writeMem(blockNum, data, writeCal = True)
        
    def eraseMem(self, eraseCal=False):
        """
        Name: U3.eraseMem(eraseCal=False)
        Args: eraseCal, set to True to erase the calibration memory instead
        Desc: The U3 uses flash memory that must be erased before writing.
              Please read section 5.2.8 of the user's guide before you do
              something you may regret.
        
        Note: Do not call this function while streaming.
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
        """
        Name: U3.eraseCal()
        Args: None
        Desc: See the description of writeMem and section 5.2.8 of the user's
              guide.
        Note: Do not call this function while streaming.
        """
        return self.eraseMem(eraseCal = True)
    
    def reset(self, hardReset = False):
        """
        Name: U3.reset(hardReset = False)
        Args: hardReset, set to True for a hard reset.
        Desc: Causes a soft or hard reset.  A soft reset consists of 
              re-initializing most variables without re-enumeration. A hard
              reset is a reboot of the processor and does cause re-enumeration.
              See section 5.2.9 of the User's guide.
        """
        command = [ 0 ] * 4
        
        #command[0] = Checksum8
        command[1] = 0x9
        command[2] = 1
        if hardReset:
            command[2] = 2
        command[3] = 0x00
        
        self.write(command)
        result = self.read(4)

    def streamConfig(self, NumChannels = 1, SamplesPerPacket = 25, InternalStreamClockFrequency = 0, DivideClockBy256 = False, Resolution = 3, ScanInterval = 1, PChannels = [30], NChannels = [31], SampleFrequency = None):
        """        
        Name: U3.streamConfig(NumChannels = 1, SamplesPerPacket = 25,
                              InternalStreamClockFrequency = 0,
                              DivideClockBy256 = False, Resolution = 3,
                              ScanInterval = 1, PChannels = [30], 
                              NChannels = [31], SampleFrequency = None)
        Args: NumChannels, the number of channels to stream
              Resolution, the resolution of the samples (0 - 3)
              PChannels, a list of channel numbers to stream
              NChannels, a list of channel options bytes
              
              Set Either:
              
              SampleFrequency, the frequency in Hz to sample
              
              -- OR --
              
              SamplesPerPacket, how many samples make one packet
              InternalStreamClockFrequency, 0 = 4 MHz, 1 = 48 MHz
              DivideClockBy256, True = divide the clock by 256
              ScanInterval, clock/ScanInterval = frequency.
        Desc: Stream mode operates on a table of channels that are scanned
              at the specified scan rate. Before starting a stream, you need 
              to call this function to configure the table and scan clock.
        
        Note: Requires U3 hardware version 1.21 or greater. 
        """
        if len(PChannels) != NumChannels:
            raise LabJackException("Length of PChannels didn't match NumChannels")
        if len(NChannels) != NumChannels:
            raise LabJackException("Length of NChannels didn't match NumChannels")
        if len(PChannels) != len(NChannels):
            raise LabJackException("Length of PChannels didn't match the length of NChannels")
            
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
        
        command = [ 0 ] * ( 12 + (NumChannels * 2) )
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = NumChannels+3
        command[3] = 0x11
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        command[6] = NumChannels
        command[7] = SamplesPerPacket
        #command[8] = Reserved
        
        command[9] |= ( InternalStreamClockFrequency & 0x01 ) << 3
        if DivideClockBy256:
            command[9] |= 1 << 2
        command[9] |= ( Resolution & 3 )
        
        t = struct.pack("<H", ScanInterval)
        command[10] = ord(t[0])
        command[11] = ord(t[1])
        
        for i in range(NumChannels):
            command[12+(i*2)] = PChannels[i]
            command[13+(i*2)] = NChannels[i]
             
        self._writeRead(command, 8, [0xF8, 0x01, 0x11])
        
        self.streamSamplesPerPacket = SamplesPerPacket
        self.streamChannelNumbers = PChannels
        self.streamNegChannels = NChannels
        
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
        Name: U3.processStreamData(result)
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
                
                if self.streamNegChannels[j] != 31:
                    # do signed
                    value = struct.unpack('<h', sample )[0]
                    singleEnded = False
                else:
                    # do unsigned
                    value = struct.unpack('<H', sample )[0]
                    singleEnded = True
                
                lvChannel = True
                if self.deviceName.lower().endswith('hv') and self.streamChannelNumbers[j] < 4:
                    lvChannel = False
               
                value = self.binaryToCalibratedAnalogVoltage(value, isLowVoltage = lvChannel, isSingleEnded = singleEnded)
                
                returnDict["AIN%s" % self.streamChannelNumbers[j]].append(value)
            
                j += 1

        return returnDict
    
    def watchdog(self, ResetOnTimeout = False, SetDIOStateOnTimeout = False, TimeoutPeriod = 60, DIOState = 0, DIONumber = 0, onlyRead=False):
        """
        Name: U3.watchdog(ResetOnTimeout = False, SetDIOStateOnTimeout = False,
                          TimeoutPeriod = 60, DIOState = 0, DIONumber = 0,
                          onlyRead = False)
        Args: Check out section 5.3.14 of the user's guide.
              Set onlyRead to True to perform only a read
        Desc: This function will write the configuration of the watchdog, unless
              onlyRead is set to True.
        
        Returns a dictonary:
        {
            'WatchDogEnabled' : True if the watchdog is enabled, otherwise False
            'ResetOnTimeout' : If True, the device will reset on timeout.
            'SetDIOStateOnTimeout' : If True, the state of a DIO will be set
            'TimeoutPeriod' : Timeout Period in seconds
            'DIOState' : The state the DIO will be set to on timeout
            'DIONumber' : Which DIO will be set on timeout
        }
        
        NOTE: Requires U3 hardware version 1.21 or greater.
        """
        command = [ 0 ] * 16
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x05
        command[3] = 0x09
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        if not onlyRead:
            command[6] = 1
        
        if ResetOnTimeout:
            command[7] |= 1 << 5
        if SetDIOStateOnTimeout:
            command[7] |= 1 << 4
        
        t = struct.pack("<H", TimeoutPeriod)
        command[8] = ord(t[0])
        command[9] = ord(t[1])
        
        command[10] = (( DIOState & 1 ) << 7) + ( DIONumber & 15)
        
        
        result = self._writeRead(command, 16, [0xF8, 0x05, 0x09])
        
        watchdogStatus = {}
        
        if result[7] == 0 or result[7] == 255:
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
    def spi(self, SPIBytes, AutoCS=True, DisableDirConfig = False, SPIMode = 'A', SPIClockFactor = 0, CSPINNum = 4, CLKPinNum = 5, MISOPinNum = 6, MOSIPinNum = 7):
        """
        Name: U3.spi(SPIBytes, AutoCS=True, DisableDirConfig = False,
                     SPIMode = 'A', SPIClockFactor = 0, CSPINNum = 4,
                     CLKPinNum = 5, MISOPinNum = 6, MOSIPinNum = 7)
        Args: SPIBytes, a list of bytes to be transferred.
              See Section 5.3.15 of the user's guide.
        Desc: Sends and receives serial data using SPI synchronous
              communication.
        
        NOTE: Requires U3 hardware version 1.21 or greater.
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
                
        return result[8:]
        
    def asynchConfig(self, Update = True, UARTEnable = True, DesiredBaud  = 9600, olderHardware = False, configurePins = True ):
        """
        Name: U3.asynchConfig(Update = True, UARTEnable = True, 
                              DesiredBaud = 9600, olderHardware = False, configurePins = True)
        Args: See section 5.3.16 of the User's Guide.
              olderHardware, If using hardware 1.21, please set olderHardware 
                             to True and read the timer configuration first.
              configurePins, Will call the configIO to set up pins for you.
        
        Desc: Configures the U3 UART for asynchronous communication. 
        
        returns a dictionary:
        {
            'Update' : True means new parameters were written
            'UARTEnable' : True means the UART is enabled
            'BaudFactor' : The baud factor being used
        }
        
        Note: Requires U3 hardware version 1.21+.
        """
        if configurePins:
            self.configIO(EnableUART=True)
        
        command = [ 0 ] * 10
            
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x02
        command[3] = 0x14
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        #command[6] = 0x00
        
        if Update:
            command[7] |= ( 1 << 7 )
        if UARTEnable:
            command[7] |= ( 1 << 6 )
        
        #command[8] = Reserved
        if olderHardware:
            command[9] = (2**8) - self.timerClockBase/DesiredBaud
        else:
            BaudFactor = (2**16) - 48000000/(2 * DesiredBaud)
            t = struct.pack("<H", BaudFactor)
            command[8] = ord(t[0])
            command[9] = ord(t[1])
        
        if olderHardware:
            result = self._writeRead(command, 10, [0xF8, 0x02, 0x14])
        else:
            result = self._writeRead(command, 10, [0xF8, 0x02, 0x14])
        
        returnDict = {}
        
        if ( ( result[7] >> 7 ) & 1 ):
            returnDict['Update'] = True
        else:
            returnDict['Update'] = False
        
        if ( ( result[7] >> 6 ) & 1):
            returnDict['UARTEnable'] = True
        else:
            returnDict['UARTEnable'] = False
            
        if olderHardware:
            returnDict['BaudFactor'] = result[9]
        else:
            returnDict['BaudFactor'] = struct.unpack("<H", struct.pack("BB", *result[8:]))[0]

        return returnDict
        
    def asynchTX(self, AsynchBytes):
        """
        Name: U3.asynchTX(AsynchBytes)
        Args: AsynchBytes, must be a list of bytes to transfer.
        Desc: Sends bytes to the U3 UART which will be sent asynchronously on
              the transmit line. See section 5.3.17 of the user's guide.
        
        returns a dictionary:
        {
            'NumAsynchBytesSent' : Number of Asynch Bytes Sent
            'NumAsynchBytesInRXBuffer' : How many bytes are currently in the
                                         RX buffer.
        }
        
        Note: Requres U3 hardware version 1.21 or greater.
        """
        if not isinstance(AsynchBytes, list):
            raise LabJackException("AsynchBytes must be a list")
        
        numBytes = len(AsynchBytes)
        
        oddPacket = False
        if numBytes%2 != 0:
            AsynchBytes.append(0)
            numBytes = numBytes+1
            oddPacket = True
        
        command = [ 0 ] * ( 8 + numBytes)
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 1 + ( numBytes/2 )
        command[3] = 0x15
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        #command[6] = 0x00
        command[7] = numBytes
        if oddPacket:
            command[7] = numBytes - 1
        
        command[8:] = AsynchBytes
        
        result = self._writeRead(command, 10, [0xF8, 0x02, 0x15])
        
        return { 'NumAsynchBytesSent' : result[7], 'NumAsynchBytesInRXBuffer' : result[8] }
        
    def asynchRX(self, Flush = False):
        """
        Name: U3.asynchRX(Flush = False)
        Args: Flush, Set to True to flush
        Desc: Reads the oldest 32 bytes from the U3 UART RX buffer
              (received on receive terminal). The buffer holds 256 bytes. See
              section 5.3.18 of the User's Guide.

        returns a dictonary:
        {
            'AsynchBytes' : List of received bytes
            'NumAsynchBytesInRXBuffer' : Number of AsynchBytes are in the RX
                                         Buffer.
        }

        Note: Requres U3 hardware version 1.21 or greater.
        """
        command = [ 0 ] * 8
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x01
        command[3] = 0x16
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        #command[6] = 0x00
        if Flush:
            command[7] = 1
        
        
        result = self._writeRead(command, 40, [0xF8, 0x11, 0x16])
        
        return { 'AsynchBytes' : result[8:], 'NumAsynchBytesInRXBuffer' : result[7] }
    
    def i2c(self, Address, I2CBytes, ResetAtStart = False, SpeedAdjust = 0, SDAPinNum = 6, SCLPinNum = 7, NumI2CBytesToReceive = 0):
        """
        Name: U3.i2c(Address, I2CBytes, ResetAtStart = False, SpeedAdjust = 0, SDAPinNum = 6, SCLPinNum = 7, NumI2CBytesToReceive = 0, AddressByte = None)
        Args: Address, the address (not shifted over)
              I2CBytes, must be a list of bytes to send.
              See section 5.3.19 of the user's guide.
              AddressByte, use this if you don't want a shift applied.
        Desc: Sends and receives serial data using I2C synchronous
              communication.
        
        Note: Requires hardware version 1.21 or greater.
        """
        if not isinstance(I2CBytes, list):
            raise LabJackException("I2CBytes must be a list")
        
        numBytes = len(I2CBytes)
        
        oddPacket = False
        if numBytes%2 != 0:
            I2CBytes.append(0)
            numBytes = numBytes + 1
            oddPacket = True
        
        command = [ 0 ] * (14 + numBytes)
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 4 + (numBytes/2)
        command[3] = 0x3B
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        if ResetAtStart:
            command[6] = (1 << 1)
        
        command[7] = SpeedAdjust
        command[8] = SDAPinNum
        command[9] = SCLPinNum
        command[10] = Address << 1
        command[12] = numBytes
        if oddPacket:
            command[12] = numBytes-1
        command[13] = NumI2CBytesToReceive
        command[14:] = I2CBytes
        
        oddResponse = False
        if NumI2CBytesToReceive%2 != 0:
            NumI2CBytesToReceive = NumI2CBytesToReceive+1
            oddResponse = True
        
        result = self._writeRead(command, 12+NumI2CBytesToReceive, [0xF8, (3+(NumI2CBytesToReceive/2)), 0x3B])
                
        if len(result) > 12:
            if oddResponse:
                return { 'AckArray' : result[8:12], 'I2CBytesRecieved' : result[12:-1] }
            else:
                return { 'AckArray' : result[8:12], 'I2CBytesRecieved' : result[12:] }
        else:
            return { 'AckArray' : result[8:], 'I2CBytesRecieved' : [] }
        
    def sht1x(self, DataPinNum = 4, ClockPinNum = 5, SHTOptions = 0xc0):
        """
        Name: U3.sht1x(DataPinNum = 4, ClockPinNum = 5, SHTOptions = 0xc0)
        Args: See section 5.3.20 of the user's guide.
              SHTOptions, see below.
        Desc: Reads temperature and humidity from a Sensirion SHT1X sensor
              (which is used by the EI-1050).

        Returns a dictonary:
        {
            'StatusReg' : SHT1X status register
            'StatusRegCRC' : SHT1X status register CRC value
            'Temperature' : The temperature in C
            'TemperatureCRC' : The CRC value for the temperature
            'Humidity' : The humidity
            'HumidityCRC' : The CRC value for the humidity
        }

        Note: Requires hardware version 1.21 or greater.
        
        SHTOptions (and proof people read documentation):
            bit 7 = Read Temperature
            bit 6 = Read Realtive Humidity
            bit 2 = Heater. 1 = on, 0 = off
            bit 1 = Reserved at 0
            bit 0 = Resolution. 1 = 8 bit RH, 12 bit T; 0 = 12 RH, 14 bit T
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
        
        result = self._writeRead(command, 16, [0xF8, 0x05, 0x39])
        
        val = (result[11]*256) + result[10]
        temp = -39.60 + 0.01*val
        
        val = (result[14]*256) + result[13]
        humid = -4 + 0.0405*val + -.0000028*(val*val)
        humid = (temp - 25)*(0.01 + 0.00008*val) + humid
        
        return { 'StatusReg' : result[8], 'StatusRegCRC' : result[9], 'Temperature' : temp, 'TemperatureCRC' : result[12] , 'Humidity' : humid, 'HumidityCRC' : result[15] }
        
    def binaryToCalibratedAnalogVoltage(self, bits, isLowVoltage = True, isSingleEnded = False, isSpecialSetting = False):
        """
        TODO: Apply real calibration constants, not just nominal.
        """
        if isLowVoltage:
            if isSingleEnded and not isSpecialSetting:
                return ( bits * 0.000037231 ) + 0
            elif isSingleEnded and isSpecialSetting:
                return (float(bits)/65536)*3.6
            else:
                return (float(bits)/65536)*4.88 - 2.44
        else:
            if isSingleEnded and not isSpecialSetting:
                return ( bits * 0.000314 ) + -10.3
            elif isSingleEnded and isSpecialSetting:
                return (float(bits)/65536)*30.4
            else:
                raise Exception, "Can't do differential on high voltage channels"
        

class FeedbackCommand(object):
    readLen = 0
    def handle(self, input):
        return None

class AIN(FeedbackCommand):
    '''
    Analog Input Feedback command

    specify the positive and negative channels to use 
    (0-16, 30 and 31 are possible)
    also specify whether to turn on longSettle or quick Sample

    returns 16-bit signed int sample
    
    >>> d.getFeedback( u3.AIN(PositiveChannel, NegativeChannel,
                              LongSettling=False, QuickSample=False) )
    '''
    def __init__(self, PositiveChannel, NegativeChannel, 
            LongSettling=False, QuickSample=False):
        validChannels = range(16) + [30, 31]
        if PositiveChannel not in validChannels:
            raise Exception("Invalid Positive Channel specified")
        if NegativeChannel not in validChannels:
            raise Exception("Invalid Negative Channel specified")
        b = PositiveChannel 
        b |= (int(bool(LongSettling)) << 6)
        b |= (int(bool(QuickSample)) << 7)
        self.cmdBytes = [ 0x01, b, NegativeChannel ]

    readLen =  2

    def handle(self, input):
        if input[1] & 0x80:
            # sign bit is set
            result = - (((input[1] & 0x7F) << 8) + input[0])
        else:
            result = (input[1] << 8) + input[0]
        return result

class WaitShort(FeedbackCommand):
    '''
    WaitShort Feedback command

    specify the number of 128us time increments to wait
    
    >>> d.getFeedback( u3.WaitShort( Time ) )
    [ None ]
    '''
    def __init__(self, Time):
        self.cmdBytes = [ 5, Time % 256 ]

class WaitLong(FeedbackCommand):
    '''
    WaitLong Feedback command
    
    specify the number of 32ms time increments to wait
    
    >>> d.getFeedback( u3.WaitLog( Time ) )
    [ None ]
    '''
    def __init__(self, Time):
        self.cmdBytes = [ 6, Time % 256 ]

class LED(FeedbackCommand):
    '''
    LED Toggle

    specify whether the LED should be on or off by truth value
    
    1 or True = On, 0 or False = Off
    
    >>> d.getFeedback( u3.LED( State ) )
    [ None ]
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
    
    >>> d.getFeedback( u3.BitStateRead( IONumber ) )
    [ 1 ]
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
    
    >>> d.getFeedback( u3.BitStateWrite( IONumber, State ) )
    [ None ]
    '''
    def __init__(self, IONumber, State):
        self.cmdBytes = [ 11, (IONumber % 20) + (int(bool(State)) << 7) ]

class BitDirRead(FeedbackCommand):
    '''
    Read the digital direction of one I/O

    IONumber: 0-7=FIO, 8-15=EIO, 16-19=CIO
    returns 1 = Output, 0 = Input
    
    >>> d.getFeedback( u3.BitDirRead( IONumber ) )
    [ 1 ]
    '''
    def __init__(self, IONumber):
        self.cmdBytes = [ 12, IONumber % 20 ]

    readLen = 1

    def handle(self, input):
        return int(bool(input[0]))

class BitDirWrite(FeedbackCommand):
    '''
    BitDirWrite Feedback command

    Set the digital direction of one I/O

    IONumber: 0-7=FIO, 8-15=EIO, 16-19=CIO
    Direction: 1 = Output, 0 = Input
    
    >>> d.getFeedback( u3.BitDirWrite( IONumber, Direction ) )
    [ None ] 
    '''
    def __init__(self, IONumber, Direction):
        self.cmdBytes = [ 13, (IONumber % 20) + (int(bool(Direction)) << 7) ]
    
class PortStateRead(FeedbackCommand):
    """
    PortStateRead Feedback command
    Reads the state of all digital I/O.
    
    >>> d.getFeedback( u3.PortStateRead() )
    [ { 'FIO' : 10, 'EIO' : 0, 'CIO' : 0 } ]
    """
    def __init__(self):
        self.cmdBytes = [ 26 ]
        
    readLen = 3
    
    def handle(self, input):
        return {'FIO' : input[0], 'EIO' : input[1], 'CIO' : input[2] }

class PortStateWrite(FeedbackCommand):
    """
    PortStateWrite Feedback command
    
    State: A list of 3 bytes representing FIO, EIO, CIO
    WriteMask: A list of 3 bytes, representing which to update.
               The Default is all ones.
    
    >>> d.getFeedback( u3.PortStateWrite( State, 
                                          WriteMask = [ 0xff, 0xff, 0xff] ) )
    [ None ]
    """
    def __init__(self, State, WriteMask = [ 0xff, 0xff, 0xff]):
        self.cmdBytes = [ 27 ] + WriteMask + State
        
class PortDirRead(FeedbackCommand):
    """
    PortDirRead Feedback command
    Reads the direction of all digital I/O.
    
    >>> d.getFeedback( u3.PortDirRead() )
    [ { 'FIO' : 10, 'EIO' : 0, 'CIO' : 0 } ]
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
    
    >>> d.getFeedback( u3.PortDirWrite( Direction, 
                                        WriteMask = [ 0xff, 0xff, 0xff] ) )
    [ None ]
    """
    def __init__(self, Direction, WriteMask = [ 0xff, 0xff, 0xff]):
        self.cmdBytes = [ 29 ] + WriteMask + Direction


class DAC8(FeedbackCommand):
    '''
    8-bit DAC Feedback command
    
    Controls a single analog output

    Dac: 0 or 1
    Value: 0-255
    
    >>> d.getFeedback( u3.DAC8( Dac, Value ) )
    [ None ]
    '''
    def __init__(self, Dac, Value):
        self.cmdBytes = [ 34 + (Dac % 2), Value % 256 ]
        
class DAC0_8(DAC8):
    """
    8-bit DAC Feedback command for DAC0
    
    Controls DAC0 in 8-bit mode.

    Value: 0-255
    
    >>> d.getFeedback( u3.DAC0_8( Value ) )
    [ None ]
    """
    def __init__(self, Value):
        DAC8.__init__(self, 0, Value)

class DAC1_8(DAC8):
    """
    8-bit DAC Feedback command for DAC1
    
    Controls DAC1 in 8-bit mode.

    Value: 0-255
    
    >>> d.getFeedback( u3.DAC1_8( Value ) )
    [ None ]
    """
    def __init__(self, Value):
        DAC8.__init__(self, 1, Value)

class DAC16(FeedbackCommand):
    '''
    16-bit DAC Feedback command

    Controls a single analog output

    Dac: 0 or 1
    Value: 0-65535
    
    >>> d.getFeedback( u3.DAC16( Dac, Value ) )
    [ None ]
    '''
    def __init__(self, Dac, Value):
        self.cmdBytes = [ 38 + (Dac % 2), Value % 256, Value >> 8 ]

class DAC0_16(DAC16):
    """
    16-bit DAC Feedback command for DAC0
    
    Controls DAC0 in 16-bit mode.

    Value: 0-65535
    
    >>> d.getFeedback( u3.DAC0_8( Value ) )
    [ None ]
    """
    def __init__(self, Value):
        DAC16.__init__(self, 0, Value)

class DAC1_16(DAC16):
    """
    16-bit DAC Feedback command for DAC1
    
    Controls DAC1 in 16-bit mode.

    Value: 0-65535
    
    >>> d.getFeedback( u3.DAC1_8( Value ) )
    [ None ]
    """
    def __init__(self, Value):
        DAC16.__init__(self, 1, Value)

class Timer(FeedbackCommand):
    """
    For reading the value of the Timer. It provides the ability to update/reset
    a given timer, and read the timer value.
    ( Section 5.2.5.14 of the User's Guide)
    
    timer: Either 0 or 1 for counter0 or counter1
     
    UpdateReset: Set True if you want to update the value
    
    Value: Only updated if the UpdateReset bit is 1.  The meaning of this
           parameter varies with the timer mode.

    >>> d.getFeedback( u3.Timer( timer, UpdateReset = False, Value = 0 ) )
    [ 12314 ]
    """
    def __init__(self, timer, UpdateReset = False, Value=0):
        if timer != 0 and timer != 1:
            raise LabJackException("Timer should be either 0 or 1.")
        if UpdateReset and Value == None:
            raise LabJackException("UpdateReset set but no value.")
            
        
        self.cmdBytes = [ (42 + (2*timer)), UpdateReset, Value % 256, Value >> 8 ]
    
    readLen = 4
    
    def handle(self, input):
        inStr = ''.join([chr(x) for x in input])
        return struct.unpack('<I', inStr )[0]

class Timer0(Timer):
    """
    For reading the value of the Timer0. It provides the ability to
    update/reset Timer0, and read the timer value.
    ( Section 5.2.5.14 of the User's Guide)
     
    UpdateReset: Set True if you want to update the value
    
    Value: Only updated if the UpdateReset bit is 1.  The meaning of this
           parameter varies with the timer mode.

    >>> d.getFeedback( u3.Timer0( UpdateReset = False, Value = 0 ) )
    [ 12314 ]
    """
    def __init__(self, UpdateReset = False, Value = 0):
        Timer.__init__(self, 0, UpdateReset, Value)

class Timer1(Timer):
    """
    For reading the value of the Timer1. It provides the ability to
    update/reset Timer1, and read the timer value.
    ( Section 5.2.5.14 of the User's Guide)
     
    UpdateReset: Set True if you want to update the value
    
    Value: Only updated if the UpdateReset bit is 1.  The meaning of this
           parameter varies with the timer mode.

    >>> d.getFeedback( u3.Timer1( UpdateReset = False, Value = 0 ) )
    [ 12314 ]
    """
    def __init__(self, UpdateReset = False, Value = 0):
        Timer.__init__(self, 1, UpdateReset, Value)

class TimerConfig(FeedbackCommand):
    """
    This IOType configures a particular timer.
    
    timer = # of the timer to configure
    
    TimerMode = See Section 2.9 for more information about the available modes.
    
    Value = The meaning of this parameter varies with the timer mode.
    
    >>> d.getFeedback( u3.TimerConfig( timer, TimerMode, Value = 0 ) )
    [ None ]
    """
    def __init__(self, timer, TimerMode, Value=0):
        '''Creates command bytes for configureing a Timer'''
        #Conditions come from pages 33-34 of user's guide
        if timer != 0 and timer != 1:
            raise LabJackException("Timer should be either 0 or 1.")
        
        if TimerMode > 13 or TimerMode < 0:
            raise LabJackException("Invalid Timer Mode.")
        
        self.cmdBytes = [43 + (timer * 2), TimerMode, Value % 256, Value >> 8]

class Timer0Config(TimerConfig):
    """
    This IOType configures Timer0.
    
    TimerMode = See Section 2.9 for more information about the available modes.
    
    Value = The meaning of this parameter varies with the timer mode.
    
    >>> d.getFeedback( u3.Timer0Config( TimerMode, Value = 0 ) )
    [ None ]
    """
    def __init__(self, TimerMode, Value = 0):
        TimerConfig.__init__(self, 0, TimerMode, Value)

class Timer1Config(TimerConfig):
    """
    This IOType configures Timer1.
    
    TimerMode = See Section 2.9 for more information about the available modes.
    
    Value = The meaning of this parameter varies with the timer mode.
    
    >>> d.getFeedback( u3.Timer1Config( TimerMode, Value = 0 ) )
    [ None ]
    """
    def __init__(self, TimerMode, Value = 0):
        TimerConfig.__init__(self, 1, TimerMode, Value)

class Counter(FeedbackCommand):
    '''
    Counter Feedback command

    Reads a hardware counter, optionally resetting it

    counter: 0 or 1
    Reset: True ( or 1 ) = Reset, False ( or 0 ) = Don't Reset

    Returns the current count from the counter if enabled.  If reset,
    this is the value before the reset.
    
    >>> d.getFeedback( u3.Counter( counter, Reset = False ) )
    [ 2183 ]
    '''
    def __init__(self, counter, Reset = False):
        self.cmdBytes = [ 54 + (counter % 2), int(bool(Reset))]

    readLen = 4

    def handle(self, input):
        inStr = ''.join([chr(x) for x in input])
        return struct.unpack('<I', inStr )[0]
    
class Counter0(Counter):
    '''
    Counter0 Feedback command

    Reads hardware counter0, optionally resetting it

    Reset: True ( or 1 ) = Reset, False ( or 0 ) = Don't Reset

    Returns the current count from the counter if enabled.  If reset,
    this is the value before the reset.
    
    >>> d.getFeedback( u3.Counter0( Reset = False ) )
    [ 2183 ]
    '''
    def __init__(self, Reset = False):
        Counter.__init__(self, 0, Reset)

class Counter1(Counter):
    '''
    Counter1 Feedback command

    Reads hardware counter1, optionally resetting it

    Reset: True ( or 1 ) = Reset, False ( or 0 ) = Don't Reset

    Returns the current count from the counter if enabled.  If reset,
    this is the value before the reset.
    
    >>> d.getFeedback( u3.Counter1( Reset = False ) )
    [ 2183 ]
    '''
    def __init__(self, Reset = False):
        Counter.__init__(self, 1, Reset)
