"""
Name: bridge.py
Desc: Defines a class for working with the wireless bridge
"""
from LabJackPython import *

class Bridge(Device):
    """
    Bridge class for working with wireless bridges
    
    >>> import bridge
    >>> d = bridge.Bridge()
    """
    
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
        
    def open(self, firstFound = True, localId = None, devNumber = None, handleOnly = False, LJSocket = "localhost:6000"): # "
        Device.open(self, 0x501, firstFound = firstFound, localId = localId, devNumber = devNumber, handleOnly = handleOnly, LJSocket = LJSocket)
    
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
    
    def VUSB(self):
        return self.readRegister(57050, numReg = 2, format = '>f')
        
    def UsbFirmwareVersion(self):
        return self.readRegister(57000)
        
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
    
    def sensorSweep(self):
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
    
    def close(self):
        self.bridge = None