"""
The U12 class. Designed to make interactions with a U12 easier.
"""

import platform
import ctypes

WINDOWS = "Windows"

try:
    staticLib = ctypes.windll.LoadLibrary("ljackuw")
except:
    raise Exception, "Could not load LabJack UW driver."    

class U12Exception(Exception):
    """Custom Exception meant for dealing specifically with U12 Exceptions.

    Error codes are either going to be a LabJackUD error code or a -1.  The -1 implies
    a python wrapper specific error.  
    
    """
    def __init__(self, ec = 0, errorString = ''):
        self.errorCode = ec
        self.errorString = errorString

        if not self.errorString:
            #try:
            self.errorString = getErrorString(ec)
            #except:
            #    self.errorString = str(self.errorCode)
    
    def __str__(self):
          return self.errorString
    
class U12(object):
    """
    U12 Class for all U12 specific commands.
    
    u12 = U12()
    
    """
    def __init__(self, id = -1, serialNumber = None):
        self.id = id
        self.serialNumber = serialNumber
        self.deviceName = "U12"
        self.streaming = False

    def open(self):
        """
        Dummy method that is used to preserve compatability with other devices in Labjack Python
        """
        pass
    
    def close(self):
        pass

    def eAnalogIn(self, channel, idNum = None, demo=0, gain=0):
        """
        Name: U12.eAnalogIn(channel, idNum = None, demo=0, gain=0)
        Args: See section 4.1 of the User's Guide
        Desc: This is a simplified version of AISample. Reads the voltage from 1 analog input

        >>> dev = U12()
        >>> dev.eAnalogIn(0)
        {'overVoltage': c_long(0), 'idnum': c_long(1), 'voltage': c_float(1.435546875)}
        """

        if idNum is None:
            idNum = self.id
        
        ljid = ctypes.c_long(idNum)
        ad0 = ctypes.c_long(999)
        ad1 = ctypes.c_float(999)

        ecode = staticLib.EAnalogIn(ctypes.byref(ljid), demo, channel, gain, ctypes.byref(ad0), ctypes.byref(ad1))

        if ecode != 0: raise U12Exception(ecode)

        return {"idnum":ljid.value, "overVoltage":ad0.value, "voltage":ad1.value}

    def eAnalogOut(self, analogOut0, analogOut1, idNum = None, demo=0):
        """
        Name: U12.eAnalogIn(analogOut0, analogOut1, idNum = None, demo=0)
        Args: See section 4.2 of the User's Guide
        Desc: This is a simplified version of AOUpdate. Sets the voltage of both analog outputs.

        >>> dev = U12()
        >>> dev.eAnalogOut(2, 2)
        {'idnum': c_long(1)}
        """

        if idNum is None:
            idNum = self.id
        
        ljid = ctypes.c_long(idNum)
        ecode = staticLib.EAnalogOut(ctypes.byref(ljid), demo, ctypes.c_float(analogOut0), ctypes.c_float(analogOut1))

        if ecode != 0: raise U12Exception(ecode)

        return {"idnum":ljid.value}

    def eCount(self, idNum = None, demo = 0, resetCounter = 0):
        """
        Name: U12.eAnalogIn(idNum = None, demo = 0, resetCounter = 0)
        Args: See section 4.3 of the User's Guide
        Desc: This is a simplified version of Counter. Reads & resets the counter (CNT).

        >>> dev = U12()
        >>> dev.eCount()
        {'count': 1383596032.0, 'ms': 251487257.0}
        """

        # Check id num
        if idNum is None:
            idNum = self.id
        
        ljid = ctypes.c_long(idNum)
        count = ctypes.c_double()
        ms = ctypes.c_double()

        ecode = staticLib.ECount(ctypes.byref(ljid), demo, resetCounter, ctypes.byref(count), ctypes.byref(ms))

        if ecode != 0: raise U12Exception(ecode)

        return {"idnum":ljid.value, "count":count.value, "ms":ms.value}

    def eDigitalIn(self, channel, idNum = None, demo = 0, readD=0):
        """
        Name: U12.eAnalogIn(channel, idNum = None, demo = 0, readD=0)
        Args: See section 4.4 of the User's Guide
        Desc: This is a simplified version of Counter. Reads & resets the counter (CNT).

        >>> dev = U12()
        >>> dev.eDigitalIn(0)
        {'state': 0, 'idnum': 1}
        """

        # Check id num
        if idNum is None:
            idNum = self.id
        
        ljid = ctypes.c_long(idNum)
        state = ctypes.c_long(999)
        
        ecode = staticLib.EDigitalIn(ctypes.byref(ljid), demo, channel, readD, ctypes.byref(state))

        if ecode != 0: raise U12Exception(ecode)

        return {"idnum":ljid.value, "state":state.value}

    def eDigitalOut(self, channel, state, idNum = None, demo = 0, writeD=0):
        """
        Name: U12.eAnalogOut(channel, state, idNum = None, demo = 0, writeD=0)
        Args: See section 4.5 of the User's Guide
        Desc: This is a simplified version of Counter. Reads & resets the counter (CNT).

        >>> dev = U12()
        >>> dev.eDigitalOut(0, 1)
        {idnum': 1}
        """

        # Check id num
        if idNum is None:
            idNum = self.id
        
        ljid = ctypes.c_long(idNum)
        
        ecode = staticLib.EDigitalOut(ctypes.byref(ljid), demo, channel, writeD, state)

        if ecode != 0: raise U12Exception(ecode)

        return {"idnum":ljid.value}

    def aiSample(self, numChannels, channels, idNum=None, demo=0, stateIOin=0, updateIO=0, ledOn=0, gains=[0, 0, 0, 0], disableCal=0):
        """
        Name: U12.aiSample(channels, idNum=None, demo=0, stateIOin=0, updateIO=0, ledOn=0, gains=[0, 0, 0, 0], disableCal=0)
        Args: See section 4.6 of the User's Guide
        Desc: Reads the voltages from 1,2, or 4 analog inputs. Also controls/reads the 4 IO ports.

        >>> dev = U12()
        >>> dev.aiSample(2, [0, 1])
        {'stateIO': [0, 0, 0, 0], 'overVoltage': 0, 'idnum': 1, 'voltages': [1.4208984375, 1.4306640625]}
        """
        
        # Check id num
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        # Check to make sure that everything is checked
        if not isIterable(channels): raise TypeError("channels must be iterable")
        if not isIterable(gains): raise TypeError("gains must be iterable")
        if len(channels) < numChannels: raise ValueError("channels must have atleast numChannels elements")
        if len(gains) < numChannels: raise ValueError("gains must have atleast numChannels elements")
        
        # Convert lists to arrays and create other ctypes
        channelsArray = listToCArray(channels, ctypes.c_long)
        gainsArray = listToCArray(gains, ctypes.c_long)
        overVoltage = ctypes.c_long(999)
        longArrayType = (ctypes.c_long * 4)
        floatArrayType = (ctypes.c_float * 4)
        voltages = floatArrayType(0, 0, 0, 0)
        stateIOin = ctypes.c_long(stateIOin)
        
        ecode = staticLib.AISample(ctypes.byref(idNum), demo, ctypes.byref(stateIOin), updateIO, ledOn, numChannels, ctypes.byref(channelsArray), ctypes.byref(gainsArray), disableCal, ctypes.byref(overVoltage), ctypes.byref(voltages))

        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value, "stateIO":stateIOin.value, "overVoltage":overVoltage.value, "voltages":voltages[0:numChannels]}

    def aiBurst(self, numChannels, channels, scanRate, numScans, idNum=None, demo=0, stateIOin=0, updateIO=0, ledOn=0, gains=[0, 0, 0, 0], disableCal=0, triggerIO=0, triggerState=0, timeout=1, transferMode=0):
        """
        Name: U12.aiBurst(numChannels, channels, scanRate, numScans, idNum=None, demo=0, stateIOin=[0, 0, 0, 0], updateIO=0, ledOn=0, gains=[0, 0, 0, 0], disableCal=0, triggerIO=0, triggerState=0, timeout=1, transferMode=0)
        Args: See section 4.7 of the User's Guide
        Desc: Reads a specified number of scans (up to 4096) at a specified scan rate (up to 8192 Hz) from 1,2, or 4 analog inputs

        >>> dev = U12()
        >>> dev.aiBurst(1, [0], 400, 10)
        {'overVoltage': 0, 'scanRate': 400.0, 'stateIOout': <u12.c_long_Array_4096 object at 0x00DB4BC0>, 'idnum': 1, 'voltages': <u12.c_float_Array_4096_Array_4 object at 0x00DB4B70>}
        """
        
        # Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        # check list sizes
        if len(channels) < numChannels: raise ValueError("channels must have atleast numChannels elements")
        if len(gains) < numChannels: raise ValueError("gains must have atleast numChannels elements")
        
        # Convert lists to arrays and create other ctypes
        channelsArray = listToCArray(channels, ctypes.c_long)
        gainsArray = listToCArray(gains, ctypes.c_long)
        scanRate = ctypes.c_float(scanRate)
        pointerArray = (ctypes.c_void_p * 4)
        arr4096_type = ctypes.c_float * 4096 
        voltages_type = arr4096_type * 4 
        voltages = voltages_type() 
        stateIOout = (ctypes.c_long * 4096)()
        overVoltage = ctypes.c_long(999)
        
        ecode = staticLib.AIBurst(ctypes.byref(idNum), demo, stateIOin, updateIO, ledOn, numChannels, ctypes.byref(channelsArray), ctypes.byref(gainsArray), ctypes.byref(scanRate), disableCal, triggerIO, triggerState, numScans, timeout, ctypes.byref(voltages), ctypes.byref(stateIOout), ctypes.byref(overVoltage), transferMode)

        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value, "scanRate":scanRate.value, "voltages":voltages, "stateIOout":stateIOout, "overVoltage":overVoltage.value}
    
    def aiStreamStart(self, numChannels, channels, scanRate, idNum=None, demo=0, stateIOin=0, updateIO=0, ledOn=0, gains=[0, 0, 0, 0], disableCal=0, readCount=0):
        """
        Name: U12.aiStreamStart(numChannels, channels, scanRate, idNum=None, demo=0, stateIOin=0, updateIO=0, ledOn=0, gains=[0, 0, 0, 0], disableCal=0, readCount=0)
        Args: See section 4.8 of the User's Guide
        Desc: Starts a hardware timed continuous acquisition

        >>> dev = U12()
        >>> dev.aiStreamStart(1, [0], 200)
        {'scanRate': 200.0, 'idnum': 1}
        """
        
        # Configure return type
        staticLib.AIStreamStart.restype = ctypes.c_long
        
        # check list sizes
        if len(channels) < numChannels: raise ValueError("channels must have atleast numChannels elements")
        if len(gains) < numChannels: raise ValueError("gains must have atleast numChannels elements")
        #if len(stateIOin) < 4: raise ValueError("stateIOin must have atleast 4 elements")

        # Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        # Convert lists to arrays and create other ctypes
        channelsArray = listToCArray(channels, ctypes.c_long)
        gainsArray = listToCArray(gains, ctypes.c_long)
        scanRate = ctypes.c_float(scanRate)
        
        ecode = staticLib.AIStreamStart(ctypes.byref(idNum), demo, stateIOin, updateIO, ledOn, numChannels, ctypes.byref(channelsArray), ctypes.byref(gainsArray), ctypes.byref(scanRate), disableCal, 0, readCount)

        if ecode != 0: raise U12Exception(ecode) # TODO: Switch this out for exception
        
        # The ID number must be saved for AIStream
        self.id = idNum.value

        self.streaming = True
        
        return {"idnum":idNum.value, "scanRate":scanRate.value}

    def aiStreamRead(self, numScans, localID=None, timeout=1):
        """
        Name: U12.aiStreamRead(numScans, localID=None, timeout=1)
        Args: See section 4.9 of the User's Guide
        Desc: Waits for a specified number of scans to be available and reads them.

        >>> dev = U12()
        >>> dev.aiStreamStart(1, [0], 200)
        >>> dev.aiStreamRead(10)
        {'overVoltage': 0, 'ljScanBacklog': 0, 'stateIOout': <u12.c_long_Array_4096 object at 0x00DF4AD0>, 'reserved': 0, 'voltages': <u12.c_float_Array_4096_Array_4 object at 0x00DF4B20>}
        """
        
        # Check to make sure that we are streaming
        if not self.streaming:
            raise U12Exception(-1, "Streaming has not started")
        
        # Check id number
        if localID is None:
            localID = self.id
            
        # Create arrays and other ctypes
        arr4096_type = ctypes.c_float * 4096 
        voltages_type = arr4096_type * 4 
        voltages = voltages_type() 
        stateIOout = (ctypes.c_long * 4096)()
        reserved = ctypes.c_long(0)
        ljScanBacklog = ctypes.c_long(99999)
        overVoltage = ctypes.c_long(999)
        
        ecode = staticLib.AIStreamRead(localID, numScans, timeout, ctypes.byref(voltages), ctypes.byref(stateIOout), ctypes.byref(reserved), ctypes.byref(ljScanBacklog), ctypes.byref(overVoltage))
        
        if ecode != 0: raise U12Exception(ecode) # TODO: Switch this out for exception
        
        return {"voltages":voltages, "stateIOout":stateIOout, "reserved":reserved.value, "ljScanBacklog":ljScanBacklog.value, "overVoltage":overVoltage.value}
    
    def aiStreamClear(self, localID=None):
        """
        Name: U12.aiClear()
        Args: See section 4.10 of the User's Guide
        Desc: This function stops the continuous acquisition. It should be called once when finished with the stream.

        >>> dev = U12()
        >>> dev.aiStreamStart(1, [0], 200)
        >>> dev.aiStreamRead(10)
        >>> dev.aiStreamClear()
        """
        
        # Check to make sure that we are streaming
        if not self.streaming:
            raise U12Exception(-1, "Streaming has not started")
        
        # Check id number
        if localID is None:
            localID = self.id
        
        ecode = staticLib.AIStreamClear(localID)

        if ecode != 0: raise U12Exception(ecode) # TODO: Switch this out for exception
        
    def aoUpdate(self, idNum=None, demo=0, trisD=None, trisIO=None, stateD=None, stateIO=None, updateDigital=0, resetCounter=0, analogOut0=0, analogOut1=0):
        """
        Name: U12.aoUpdate()
        Args: See section 4.11 of the User's Guide
        Desc: Sets the voltages of the analog outputs. Also controls/reads all 20 digital I/O and the counter.

        >>> dev = U12()
        >>> dev.aoUpdate()
        >>> {'count': 2, 'stateIO': 3, 'idnum': 1, 'stateD': 0}
        """
        
        # Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        #  Check tris and state arguments
        if updateDigital > 0:
            if trisD is None: raise ValueError("keyword argument trisD must be set")
            if trisIO is None: raise ValueError("keyword argument trisIO must be set")
            if stateD is None: raise ValueError("keyword argument stateD must be set")
            if stateIO is None: raise ValueError("keyword argument stateIO must be set")

        # Create ctypes
        if stateD is None: stateD = ctypes.c_long(0)
        else: stateD = ctypes.c_long(stateD)
        if stateIO is None: stateIO = ctypes.c_long(0)
        else: stateIO = ctypes.c_long(stateIO)
        count = ctypes.c_ushort(999)
        
        # Create arrays and other ctypes
        ecode = staticLib.AOUpdate(ctypes.byref(idNum), demo, trisD, trisIO, ctypes.byref(stateD), ctypes.byref(stateIO), updateDigital, resetCounter, ctypes.byref(count), ctypes.c_float(analogOut0), ctypes.c_float(analogOut1))
        
        if ecode != 0: raise U12Exception(ecode) # TODO: Switch this out for exception
        
        return {"idnum":idNum.value, "stateD":stateD.value, "stateIO":stateIO.value, "count":count.value}

    def asynchConfig(self, fullA, fullB, fullC, halfA, halfB, halfC, idNum=None, demo=None, timeoutMult=1, configA=0, configB=0, configTE=0):
        """
        Name: U12.asynchConfig(fullA, fullB, fullC, halfA, halfB, halfC, idNum=None, demo=None, timeoutMult=1, configA=0, configB=0, configTE=0)
        Args: See section 4.12 of the User's Guide
        Desc: Requires firmware V1.1 or higher. This function writes to the asynch registers and sets the direction of the D lines (input/output) as needed.

        >>> dev = U12()
        >>> dev.asynchConfig(96,1,1,22,2,1)
        >>> {'idNum': 1}
        """
        
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        ecode = staticLib.AsynchConfig(ctypes.byref(idNum), demo, timeoutMult, configA, configB, configTE, fullA, fullB, fullC, halfA, halfB, halfC)
        
        if ecode != 0: raise U12Exception(ecode) # TODO: Switch this out for exception
        
        return {"idNum":idNum.value}
    
    def asynch(self, baudrate, data, idNum=None, demo=0, portB=0, enableTE=0, enableTO=0, enableDel=0, numWrite=0, numRead=0):
        """
        Name: U12.asynchConfig(fullA, fullB, fullC, halfA, halfB, halfC, idNum=None, demo=None, timeoutMult=1, configA=0, configB=0, configTE=0)
        Args: See section 4.13 of the User's Guide
        Desc: Requires firmware V1.1 or higher. This function writes to the asynch registers and sets the direction of the D lines (input/output) as needed.

        >>> dev = U12()
        >>> dev.asynch(96,1,1,22,2,1)
        >>> dev.asynch(19200, [0, 0])
        >>> {'data': <u12.c_long_Array_18 object at 0x00DEFB70>, 'idnum': <type 'long'>}
        """
        
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        # Check size of data
        if len(data) > 18: raise ValueError("data can not be larger than 18 elements")
        
        # Make data 18 elements large
        dataArray = [0] * 18
        for i in range(0, len(data)):
            dataArray[i] = data[i]
        print dataArray
        dataArray = listToCArray(dataArray, ctypes.c_long)
        
        ecode = staticLib.Asynch(ctypes.byref(idNum), demo, portB, enableTE, enableTO, enableDel, baudrate, numWrite, numRead, ctypes.byref(dataArray))
        
        if ecode != 0: raise U12Exception(ecode) # TODO: Switch this out for exception
        
        return {"idnum":long, "data":dataArray}
    
    def bitsToVolts(self, chnum, chgain, bits):
        """
        Name: U12.bitsToVolts(chnum, chgain, bits)
        Args: See section 4.14 of the User's Guide
        Desc: Converts a 12-bit (0-4095) binary value into a LabJack voltage. No hardware communication is involved.

        >>> dev = U12()
        >>> dev.bitsToVolts(0, 0, 2662)
        >>> {'volts': 2.998046875}
        """
        volts = ctypes.c_float()
        ecode = staticLib.BitsToVolts(chnum, chgain, bits, ctypes.byref(volts))

        if ecode != 0: print ecode

        return {"volts" : volts.value}

    def voltsToBits(self, chnum, chgain, volts):
        """
        Name: U12.voltsToBits(chnum, chgain, bits)
        Args: See section 4.15 of the User's Guide
        Desc: Converts a voltage to it's 12-bit (0-4095) binary representation. No hardware communication is involved.

        >>> dev = U12()
        >>> dev.voltsToBits(0, 0, 3)
        >>> {'bits': 2662}
        """

        bits = ctypes.c_long(999)
        ecode = staticLib.VoltsToBits(chnum, chgain, ctypes.c_float(volts), ctypes.byref(bits))

        if ecode != 0: raise U12Exception(ecode)

        return {"bits" : bits.value}
    
    def counter(self, idNum=None, demo=0, resetCounter=0, enableSTB=1):
        """
        Name: U12.counter(idNum=None, demo=0, resetCounter=0, enableSTB=1)
        Args: See section 4.15 of the User's Guide
        Desc: Converts a voltage to it's 12-bit (0-4095) binary representation. No hardware communication is involved.

        >>> dev = U12()
        >>> dev.counter(0, 0, 3)
        >>> {'bits': 2662}
        """
        
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        # Create ctypes
        stateD = ctypes.c_long(999)
        stateIO = ctypes.c_long(999)
        count = ctypes.c_ulong(999)
        
        print idNum
        ecode = staticLib.Counter(ctypes.byref(idNum), demo, ctypes.byref(stateD), ctypes.byref(stateIO), resetCounter, enableSTB, ctypes.byref(count))

        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value, "stateD": stateD.value, "stateIO":stateIO.value, "count":count.value}

    def digitalIO(self, idNum=None, demo=0, trisD=None, trisIO=None, stateD=None, stateIO=None, updateDigital=0):
        """
        Name: U12.digitalIO(idNum=None, demo=0, trisD=None, trisIO=None, stateD=None, stateIO=None, updateDigital=0)
        Args: See section 4.17 of the User's Guide
        Desc: Reads and writes to all 20 digital I/O.

        >>> dev = U12()
        >>> dev.digitalIO()
        >>> {'stateIO': 0, 'stateD': 0, 'idnum': 1, 'outputD': 0, 'trisD': 0}
        """
        
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)

        # Check tris and state parameters
        if updateDigital > 0:
            if trisD is None: raise ValueError("keyword argument trisD must be set")
            if trisIO is None: raise ValueError("keyword argument trisIO must be set")
            if stateD is None: raise ValueError("keyword argument stateD must be set")
            if stateIO is None: raise ValueError("keyword argument stateIO must be set")
        
        # Create ctypes
        if trisD is None: trisD = ctypes.c_long(999)
        else:trisD = ctypes.c_long(trisD)
        if stateD is None:stateD = ctypes.c_long(999)
        else: stateD = ctypes.c_long(stateD)
        if stateIO is None: stateIO = ctypes.c_long(0)
        else: stateIO = ctypes.c_long(stateIO)
        outputD = ctypes.c_long(999)
        
        # Check trisIO
        if trisIO is None: trisIO = 0

        ecode = staticLib.DigitalIO(ctypes.byref(idNum), demo, ctypes.byref(trisD), trisIO, ctypes.byref(stateD), ctypes.byref(stateIO), updateDigital, ctypes.byref(outputD))
        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value, "trisD":trisD.value, "stateD":stateD.value, "stateIO":stateIO.value, "outputD":outputD.value}
        
    def getDriverVersion(self):
        """
        Name: U12.getDriverVersion()
        Args: See section 4.18 of the User's Guide
        Desc: Returns the version number of ljackuw.dll. No hardware communication is involved.

        >>> dev = U12()
        >>> dev.getDriverVersion()
        >>> 1.21000003815
        """
        staticLib.GetDriverVersion.restype = ctypes.c_float
        return staticLib.GetDriverVersion()

    def getFirmwareVersion(self, idNum=None):
        """
        Name: U12.getErrorString(idnum=None)
        Args: See section 4.20 of the User's Guide
        Desc: Retrieves the firmware version from the LabJack's processor

        >>> dev = U12()
        >>> dev.getFirmwareVersion()
        >>> Unkown error
        """
        
        # Check ID number
        if idNum is None: idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        staticLib.GetFirmwareVersion.restype = ctypes.c_float
        firmware = staticLib.GetFirmwareVersion(ctypes.byref(idNum))

        if firmware > 512: raise U12Exception(firmware-512)

        return {"idnum" : idNum.value, "firmware" : firmware}
    
    def getWinVersion(self):
        """
        Name: U12.getErrorString()
        Args: See section 4.21 of the User's Guide
        Desc: Uses a Windows API function to get the OS version
        
        >>> dev = U12()
        >>> dev.getWinVersion()
        >>> {'majorVersion': 5L, 'minorVersion': 1L, 'platformID': 2L, 'buildNumber': 2600L, 'servicePackMajor': 2L, 'servicePackMinor': 0L}
        """
        
        # Create ctypes
        majorVersion = ctypes.c_ulong()
        minorVersion = ctypes.c_ulong()
        buildNumber = ctypes.c_ulong()
        platformID = ctypes.c_ulong()
        servicePackMajor = ctypes.c_ulong()
        servicePackMinor = ctypes.c_ulong()
        
        ecode = staticLib.GetWinVersion(ctypes.byref(majorVersion), ctypes.byref(minorVersion), ctypes.byref(buildNumber), ctypes.byref(platformID), ctypes.byref(servicePackMajor), ctypes.byref(servicePackMinor))
        
        if ecode != 0: raise U12Exception(ecode)
        
        return {"majorVersion":majorVersion.value, "minorVersion":minorVersion.value, "buildNumber":buildNumber.value, "platformID":platformID.value, "servicePackMajor":servicePackMajor.value, "servicePackMinor":servicePackMinor.value}
    
    def listAll(self):
        """
        Name: U12.listAll()
        Args: See section 4.22 of the User's Guide
        Desc: Searches the USB for all LabJacks, and returns the serial number and local ID for each
        
        >>> dev = U12()
        >>> dev.listAll()
        >>> {'serialnumList': <u12.c_long_Array_127 object at 0x00E2AD50>, 'numberFound': 1, 'localIDList': <u12.c_long_Array_127 object at 0x00E2ADA0>}
        """
        
        # Create arrays and ctypes
        productIDList = listToCArray([0]*127, ctypes.c_long)
        serialnumList = listToCArray([0]*127, ctypes.c_long)
        localIDList = listToCArray([0]*127, ctypes.c_long)
        powerList = listToCArray([0]*127, ctypes.c_long)
        arr127_type = ctypes.c_long * 127 
        calMatrix_type = arr127_type * 20
        calMatrix = calMatrix_type() 
        reserved = ctypes.c_long()
        numberFound = ctypes.c_long()
        
        ecode = staticLib.ListAll(ctypes.byref(productIDList), ctypes.byref(serialnumList), ctypes.byref(localIDList), ctypes.byref(powerList), ctypes.byref(calMatrix), ctypes.byref(numberFound), ctypes.byref(reserved), ctypes.byref(reserved))
        if ecode != 0: raise U12Exception(ecode)
        
        return {"serialnumList": serialnumList, "localIDList":localIDList, "numberFound":numberFound.value}
        
    def localID(self, localID, idNum=None):
        """
        Name: U12.localID(localID, idNum=None)
        Args: See section 4.23 of the User's Guide
        Desc: Changes the local ID of a specified LabJack
        
        >>> dev = U12()
        >>> dev.localID(1)
        >>> {'idnum':1}
        """
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        ecode = staticLib.LocalID(ctypes.byref(idNum), localID)
        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value}
    
    def noThread(self, noThread, idNum=None):
        """
        Name: U12.localID(noThread, idNum=None)
        Args: See section 4.24 of the User's Guide
        Desc: This function is needed when interfacing TestPoint to the LabJack DLL on Windows 98/ME
        
        >>> dev = U12()
        >>> dev.noThread(1)
        >>> {'idnum':1}
        """
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        ecode = staticLib.NoThread(ctypes.byref(idNum), noThread)
        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value}
    
    def pulseOut(self, bitSelect, numPulses, timeB1, timeC1, timeB2, timeC2, idNum=None, demo=0, lowFirst=0):
        """
        Name: U12.pulseOut(bitSelect, numPulses, timeB1, timeC1, timeB2, timeC2, idNum=None, demo=0, lowFirst=0)
        Args: See section 4.25 of the User's Guide
        Desc: This command creates pulses on any/all of D0-D7
        
        >>> dev = U12()
        >>> dev.pulseOut(0, 1, 1, 1, 1, 1)
        >>> {'idnum':1}
        """
        
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        ecode = staticLib.PulseOut(ctypes.byref(idNum), demo, lowFirst, bitSelect, numPulses, timeB1, timeC1, timeB2, timeC2)
        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value}
    
    def pulseOutStart(self, bitSelect, numPulses, timeB1, timeC1, timeB2, timeC2, idNum=None, demo=0, lowFirst=0):
        """
        Name: U12.pulseOutStart(bitSelect, numPulses, timeB1, timeC1, timeB2, timeC2, idNum=None, demo=0, lowFirst=0)
        Args: See section 4.26 of the User's Guide
        Desc: PulseOutStart and PulseOutFinish are used as an alternative to PulseOut (See PulseOut for more information)
        
        >>> dev = U12()
        >>> dev.pulseOutStart(0, 1, 1, 1, 1, 1)
        >>> {'idnum':1}
        """
        
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        ecode = staticLib.PulseOutStart(ctypes.byref(idNum), demo, lowFirst, bitSelect, numPulses, timeB1, timeC1, timeB2, timeC2)
        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value}

    def pulseOutFinish(self, timeoutMS, idNum=None, demo=0):
        """
        Name: U12.pulseOutFinish(timeoutMS, idNum=None, demo=0)
        Args: See section 4.27 of the User's Guide
        Desc: See PulseOutStart for more information
        
        >>> dev = U12()
        >>> dev.pulseOutStart(0, 1, 1, 1, 1, 1)
        >>> dev.pulseOutFinish(100)
        >>> {'idnum':1}
        """
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        ecode = staticLib.PulseOutFinish(ctypes.byref(idNum), demo, timeoutMS)
        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value}
    
    def pulseOutCalc(self, frequency):
        """
        Name: U12.pulseOutFinish(frequency)
        Args: See section 4.28 of the User's Guide
        Desc: This function can be used to calculate the cycle times for PulseOut or PulseOutStart.
        
        >>> dev = U12()
        >>> dev.pulseOutCalc(100)
        >>> {'frequency': 100.07672882080078, 'timeB': 247, 'timeC': 1}
        """
        
        # Create ctypes
        frequency = ctypes.c_float(frequency)
        timeB = ctypes.c_long(0)
        timeC = ctypes.c_long(0)
        
        ecode = staticLib.PulseOutCalc(ctypes.byref(frequency), ctypes.byref(timeB), ctypes.byref(timeC))
        if ecode != 0: raise U12Exception(ecode)
        
        return {"frequency":frequency.value, "timeB":timeB.value, "timeC":timeC.value}
    
    def reEnum(self, idNum=None):
        """
        Name: U12.reEnum(idNum=None)
        Args: See section 4.29 of the User's Guide
        Desc: Causes the LabJack to electrically detach from and re-attach to the USB so it will re-enumerate
        
        >>> dev = U12()
        >>> dev.reEnum()
        >>> {'idnum': 1}
        """
        
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        ecode = staticLib.ReEnum(ctypes.byref(idNum))
        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value}
    
    def reset(self, idNum=None):
        """
        Name: U12.reset(idNum=None)
        Args: See section 4.30 of the User's Guide
        Desc: Causes the LabJack to reset after about 2 seconds
        
        >>> dev = U12()
        >>> dev.reset()
        >>> {'idnum': 1}
        """
        
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        ecode = staticLib.Reset(ctypes.byref(idNum))
        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value}
    
    def resetLJ(self, idNum=None):
        """
        Name: U12.resetLJ(idNum=None)
        Args: See section 4.30 of the User's Guide
        Desc: Causes the LabJack to reset after about 2 seconds
        
        >>> dev = U12()
        >>> dev.resetLJ()
        >>> {'idnum': 1}
        """
        return reset(idNum)
    
    def sht1X(self, idNum=None, demo=0, softComm=0, mode=0, statusReg=0):
        """
        Name: U12.sht1X(idNum=None, demo=0, softComm=0, mode=0, statusReg=0)
        Args: See section 4.31 of the User's Guide
        Desc: This function retrieves temperature and/or humidity readings from an SHT1X sensor.
        
        >>> dev = U12()
        >>> dev.sht1X()
        >>> {'tempC': 24.69999885559082, 'rh': 39.724445343017578, 'idnum': 1, 'tempF': 76.459999084472656}
        """
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        # Create ctypes
        tempC = ctypes.c_float(0)
        tempF = ctypes.c_float(0)
        rh = ctypes.c_float(0)
        
        ecode = staticLib.SHT1X(ctypes.byref(idNum), demo, softComm, mode, statusReg, ctypes.byref(tempC), ctypes.byref(tempF), ctypes.byref(rh))
        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value, "tempC":tempC.value, "tempF":tempF.value, "rh":rh.value}
    
    def shtComm(self, numWrite, numRead, datatx, idNum=None, softComm=0, waitMeas=0, serialReset=0, dataRate=0):
        """
        Name: U12.shtComm(numWrite, numRead, datatx, idNum=None, softComm=0, waitMeas=0, serialReset=0, dataRate=0)
        Args: See section 4.32 of the User's Guide
        Desc: Low-level public function to send and receive up to 4 bytes to from an SHT1X sensor
        """
        
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        # Check size of datatx
        if len(datatx) != 4: raise ValueError("datatx must have exactly 4 elements")
        
        # Create ctypes
        datatx = listToCArray(datatx, ctypes.c_ubyte)
        datarx = (ctypes.c_ubyte * 4)((0) * 4)
        
        ecode = staticLib.SHTComm(ctypes.byref(idNum), softComm, waitMeas, serialReset, dataRate, numWrite, numRead, ctypes.byref(datatx), ctypes.byref(datarx))
        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value, "datarx":datarx}
    
    def shtCRC(self, numWrite, numRead, datatx, datarx, statusReg=0):
        """
        Name: U12.shtCRC(numWrite, numRead, datatx, datarx, statusReg=0)
        Args: See section 4.33 of the User's Guide
        Desc: Checks the CRC on an SHT1X communication
        """
        # Create ctypes
        datatx = listToCArray(datatx, ctypes.c_ubyte)
        datarx = listToCArray(datarx, ctypes.c_ubyte)
        
        return staticLib.SHTCRC(statusReg, numWrite, numRead, ctypes.byref(datatx), ctypes.byref(datarx))

    def synch(self, mode, numWriteRead, data, idNum=None, demo=0, msDelay=0, husDelay=0, controlCS=0, csLine=None, csState=0, configD=0):
        """
        Name: U12.synch(mode, numWriteRead, data, idNum=None, demo=0, msDelay=0, husDelay=0, controlCS=0, csLine=None, csState=0, configD=0)
        Args: See section 4.35 of the User's Guide
        Desc: This function retrieves temperature and/or humidity readings from an SHT1X sensor.
        """
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        if controlCS > 0 and csLine is None: raise ValueError("csLine must be specified")
        
        # Make sure data is 18 elements
        cData = [0] * 18
        for i in range(0, len(data)):
            cData[i] = data[i]
        cData = listToCArray(cData, ctypes.c_long)
        
        ecode = staticLib.Synch(ctypes.byref(idNum), demo, mode, msDelay, husDelay, controlCS, csLine, csState, configD, numWriteRead, ctypes.byref(cData))
        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value, "data":cData}
    
    def watchdog(self, active, timeout, activeDn, stateDn, idNum=None, demo=0, reset=0):
        """
        Name: U12.watchdog(active, timeout, activeDn, stateDn, idNum=None, demo=0, reset=0)
        Args: See section 4.35 of the User's Guide
        Desc: Controls the LabJack watchdog function.
        
        >>> dev = U12()
        >>> dev.watchdog(1, 1, [0, 0, 0], [0, 0, 0])
        >>> {'idnum': 1}
        """
        
        #Check id number
        if idNum is None:
            idNum = self.id
        idNum = ctypes.c_long(idNum)
        
        if len(activeDn) is not 3: raise ValueError("activeDn must have 3 elements")
        if len(stateDn) is not 3: raise Value("stateDn must have 3 elements")
        
        ecode = staticLib.Watchdog(ctypes.byref(idNum), demo, active, timeout, reset, activeDn[0], activeDn[1], activeDn[2], stateDn[0], stateDn[1], stateDn[2])
        if ecode != 0: raise U12Exception(ecode)
        
        return {"idnum":idNum.value}
        
    def readMem(self, address, idnum = None):
        """
        Name: U12.readMem(address, idnum=None)
        Args: See section 4.36 of the User's Guide
        Desc: Reads 4 bytes from a specified address in the LabJack's nonvolatile memory
        
        >>> dev = U12()
        >>> dev.readMem(0)
        >>> [5, 246, 16, 59]
        """
        
        if address is None:
            raise Exception, "Must give an Address."
        
        if idnum is None:
            idnum = self.id
            
        ljid = ctypes.c_ulong(idnum)
        ad0 = ctypes.c_ulong()
        ad1 = ctypes.c_ulong()
        ad2 = ctypes.c_ulong()
        ad3 = ctypes.c_ulong()

        ec = staticLib.ReadMem(ctypes.byref(ljid), ctypes.c_long(address), ctypes.byref(ad3), ctypes.byref(ad2), ctypes.byref(ad1), ctypes.byref(ad0))
        if ec != 0: raise U12Exception(ec)
        
        addr = [0] * 4
        addr[0] = int(ad3.value & 0xff)
        addr[1] = int(ad2.value & 0xff)
        addr[2] = int(ad1.value & 0xff)
        addr[3] = int(ad0.value & 0xff)

        return addr
    
    def writeMem(self, address, data, idnum=None, unlocked=False):
        """
        Name: U12.writeMem(self, address, data, idnum=None, unlocked=False)
        Args: See section 4.37 of the User's Guide
        Desc: Writes 4 bytes to the LabJack's 8,192 byte nonvolatile memory at a specified address.
        
        >>> dev = U12()
        >>> dev.writeMem(0, [5, 246, 16, 59])
        >>> 1
        """
        if address is None or data is None:
            raise Exception, "Must give both an Address and data."
        if type(data) is not list or len(data) != 4:
            raise Exception, "Data must be a list and have a length of 4"
        
        if idnum is None:
            idnum = self.id
        
        ljid = ctypes.c_ulong(idnum)
        ec = staticLib.WriteMem(ctypes.byref(ljid), int(unlocked), address, data[3] & 0xff, data[2] & 0xff, data[1] & 0xff, data[0] & 0xff)
        if ec != 0: raise U12Exception(ec)
        
        return ljid.value
        
    def LJHash(self, hashStr, size):
        outBuff = (ctypes.c_char * 16)()
        retBuff = ''
        
        staticLib = ctypes.windll.LoadLibrary("ljackuw")
        
        ec = staticLib.LJHash(ctypes.cast(hashStr, ctypes.POINTER(ctypes.c_char)),
                              size, 
                              ctypes.cast(outBuff, ctypes.POINTER(ctypes.c_char)), 
                              0)
        if ec != 0: raise U12Exception(ec)

        for i in range(16):
            retBuff += outBuff[i]
            
        return retBuff

def isIterable(var):
    try:
        iter(var)
        return True
    except:
        return False
    
def listToCArray(list, dataType):
    arrayType = dataType * len(list)
    array = arrayType()
    for i in range(0,len(list)):
        array[i] = list[i]
    
    return array

def cArrayToList(array):
    list = []
    for item in array:
        list.append(item)
    
    return list

def getErrorString(errorcode):
    """
    Name: U12.getErrorString(errorcode)
    Args: See section 4.19 of the User's Guide
    Desc: Converts a LabJack errorcode, returned by another function, into a string describing the error. No hardware communication is involved.

    >>> dev = U12()
    >>> dev.getErrorString(1)
    >>> Unkown error
    """
    errorString = ctypes.c_char_p(" "*50)
    staticLib.GetErrorString(errorcode, errorString)
    return errorString.value

# Check os
if platform.system() is not WINDOWS:
    raise OSError("Python support for the U12 is only available for Windows")
