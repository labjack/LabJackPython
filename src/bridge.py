"""
Name: bridge.py
Desc: Defines a class for working with the wireless bridge
"""
from LabJackPython import *

if os.name == "nt":
    if skymoteLib is None:
        raise ImportError("Couldn't load liblabjackusb.dll. Please install, and try again.")
        
    


class Bridge(Device):
    """
    Bridge class for working with wireless bridges
    
    >>> import bridge
    >>> d = bridge.Bridge()
    """
    # ------------------ Object Functions ------------------
    # These functions are part of object interaction in python
    
    def __init__(self, handle = None, localId = None, serialNumber = None, autoOpen = True, **kargs):
        Device.__init__(self, None, devType = 0x501)
    
        self.handle = handle
        self.localId = localId
        self.serialNumber = serialNumber
        self.devType = 0x501
        self.unitId = 0
        self.debug = True
        self.zeroPrepend = False
        self.modbusPrependZeros = False
        
        if autoOpen:
            self.open(**kargs)
        
    def open(self, firstFound = True, localId = None, devNumber = None, handleOnly = False, LJSocket = "localhost:6000"): #"
        Device.open(self, 0x501, firstFound = firstFound, localId = localId, devNumber = devNumber, handleOnly = handleOnly, LJSocket = LJSocket)
    
    if os.name == "nt":
        def _readFromUDDriver(self, numBytes, stream, modbus):
            newA = (ctypes.c_byte*numBytes)()
            readBytes = skymoteLib.LJUSB_IntRead(self.handle, 0x81, ctypes.byref(newA), numBytes)
            return [(newA[i] & 0xff) for i in range(readBytes)]
            
        def _writeToUDDriver(self, writeBuffer, modbus):
            newA = (ctypes.c_byte*len(writeBuffer))(0) 
            for i in range(len(writeBuffer)):
                newA[i] = ctypes.c_byte(writeBuffer[i])
            
            writeBytes = skymoteLib.LJUSB_IntWrite(self.handle, 1, ctypes.byref(newA), len(writeBuffer))
            
            if(writeBytes != len(writeBuffer)):
                raise LabJackException( "Could only write %s of %s bytes." % (writeBytes, len(writeBuffer) ) )
    
    def read(self, numBytes, stream = False, modbus = False):
        result = Device.read(self, 64, stream, modbus)
        return result[:numBytes]
    
    def readRegister(self, addr, numReg = None, format = None, unitId = None):
        if unitId is None:
            return Device.readRegister(self, addr, numReg, format, self.unitId)
        else:
            return Device.readRegister(self, addr, numReg, format, unitId)
            
    def writeRegister(self, addr, value, unitId = None):
        if unitId is None:
            return Device.writeRegister(self, addr, value, unitId = self.unitId)
        else:
            return Device.writeRegister(self, addr, value, unitId = unitId)
    
    # ------------------ Convenience Functions ------------------
    # These functions call read register for you. 
        
    def usbFirmwareVersion(self):
        left, right = self.readRegister(57000, format = 'BB')
        return float("%s.%02d" % (left, right))
    
    def usbBufferStatus(self):
        return self.readRegister(57001)
    
    def numUSBRX(self):
        return self.readRegister(57002, numReg = 2, format = '>I')
        
    def numUSBTX(self):
        return self.readRegister(57004, numReg = 2, format = '>I')
        
    def numPIBRX(self):
        return self.readRegister(57006, numReg = 2, format = '>I')
        
    def numPIBTX(self):
        return self.readRegister(57008, numReg = 2, format = '>I')
        
    def lastUsbError(self):
        return self.readRegister(57010)
    
    def dmOverflows(self):
        return self.readRegister(57011)
        
    def numPibTos(self):
        return self.readRegister(57014)
        
    def numUsbTos(self):
        return self.readRegister(57015)
    
    def vUsb(self):
        return self.readRegister(57050, numReg = 2, format = '>f')
    
    def vJack(self):
        return self.readRegister(57052, numReg = 2, format = '>f')
    
    def vSt(self):
        return self.readRegister(57054, numReg = 2, format = '>f')
    
    # ------------------ Mote Functions ------------------
    # These functions help you work with the motes.
    
    def listMotes(self):
        numMotes = self.readRegister(59200, numReg = 2, format = '>I')
        
        
        connectedMotes = []
        
        moteIds = self.readRegister(59202, numReg = numMotes, format = ">" + "H" *numMotes )
        
        for moteId in moteIds:
            connectedMotes.append(Mote(self, moteId))
        
        return connectedMotes
        
    def makeMote(self, moteId):
        return Mote(self, moteId)
    


class Mote(object):
    # ------------------ Object Functions ------------------
    # These functions are part of object interaction in python
    def __init__(self, bridge, moteId):
        self.bridge = bridge
        self.moteId = moteId
        
    def __repr__(self):
        return str(self)
    
    def __str__(self):
        return "<Mote Object with ID = %s>" % self.moteId
        
    def readRegister(self, addr, numReg = None, format = None):
        return self.bridge.readRegister(addr, numReg = numReg, format = format, unitId = self.moteId)
    
    def writeRegister(self, addr, value):
        return self.bridge.writeRegister(addr, value, unitId = self.moteId)
        
    def close(self):
        self.bridge = None
    
    # ------------------ Convenience Functions ------------------
    # These functions call read register for you. 
    
    def sensorSweep(self):
        """
        Performs a sweep of all the sensors on the sensor mote.
        """
        rxLqi, txLqi, battery, temp, light, motion, sound, rh = self.readRegister(12000, numReg = 16, format = ">" + "f"*8)
        
        results = dict()
        results['RxLQI'] = rxLqi
        results['TxLQI'] = txLqi
        results['Battery'] = battery
        results['Temp'] = temp
        results['Light'] = light
        results['Motion'] = motion
        results['Sound'] = sound
        results['RH'] = rh
        
        return results
        
    def panId(self):
        return self.readRegister(50000)
        
    def sleepTime(self):
        return self.readRegister(50100, numReg = 2, format = ">I")