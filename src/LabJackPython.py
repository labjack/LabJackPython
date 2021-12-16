"""
Multi-Platform Python wrapper that implements functions from the LabJack
Windows UD Driver, and the Exodriver.

This Python wrapper is intended to make working with your LabJack device easy.
The functions contained in this module are helper and device agnostic functions.
This module provides the base Device class which the U3, U6, and UE9 classes
inherit from.

A typical user should start with their device's module, such as u3.py.
"""
# We use the 'with' keyword to manage the thread-safe device lock. 
# It's built-in on 2.6; 2.5 requires an import.
from __future__ import with_statement

import atexit  # For auto-closing devices
import socket
import ctypes  # import after socket or cygwin crashes "Aborted (core dump)"
import errno
import sys
import threading  # For a thread-safe device lock
import logging

from struct import pack, unpack

import Modbus


LABJACKPYTHON_VERSION = "2.0.5"
__version__ = LABJACKPYTHON_VERSION

SOCKET_TIMEOUT = 3
LJSOCKET_TIMEOUT = 62
BROADCAST_SOCKET_TIMEOUT = 1
MAX_USB_PACKET_LENGTH = 64

NUMBER_OF_UNIQUE_LABJACK_PRODUCT_IDS = 4

_os_name = ""  # Set to "nt" or "posix" in _loadLibrary.

_use_ptr = True  # Set to True or False in _loadLibrary. Indicates whether to use
                 # the Ptr version of certain UD calls or not. Windows only.

_use_py2 = sys.version_info < (3, 0)  # Indicates to use Python 2.x or
                                      # Python 3+ when needed.


class LabJackException(Exception):
    """Custom Exception meant for dealing specifically with LabJack Exceptions.

    Error codes are either going to be a LabJackUD error code or a -1.  The -1
    implies a Python wrapper specific error.

    WINDOWS ONLY
    If errorString is not specified then errorString is set by errorCode.
    """
    def __init__(self, ec = 0, errorString = ''):
        self.errorCode = ec
        self.errorString = errorString

        if not self.errorString:
            try:
                pString = ctypes.create_string_buffer(256)
                staticLib.ErrorToString(ctypes.c_long(self.errorCode), ctypes.byref(pString))
                self.errorString = pString.value.decode("ascii").split("\0", 1)[0]
            except:
                self.errorString = str(self.errorCode)

    def __str__(self):
          return self.errorString


class LowlevelErrorException(LabJackException):
    """Raised when a low-level command raises an error."""
    pass


class NullHandleException(LabJackException):
    """Raised when the return value of OpenDevice is null."""
    def __init__(self, info=None):
        if info is None:
            # Default additional information message.
            info = "Please check that the device you are trying to open is connected."
        else:
            # Set additional information message.
            info = str(info)

        self.errorString = "Couldn't open device. " + info


def errcheck(ret, func, args):
    """
    Whenever a function is called through ctypes, the return value is passed to
    this function to be checked for errors.
    
    Support for errno didn't come until 2.6, so Python 2.5 people should 
    upgrade.
    """
    if ret == -1:
        try:
            ec = ctypes.get_errno()
            raise LabJackException(ec, "Exodriver returned error number %s" % ec)
        except AttributeError:
            raise LabJackException(-1, "Exodriver returned an error, but LabJackPython is unable to read the error code. Upgrade to Python 2.6 for this functionality.")
    else:
        return ret

def _loadLinuxSo():
    """
    Attempts to load the liblabjackusb.so for Linux.
    """
    l = ctypes.CDLL("liblabjackusb.so", use_errno=True)
    l.LJUSB_StreamTO.errcheck = errcheck
    l.LJUSB_Read.errcheck = errcheck
    return l

def _loadMacDylib():
    """
    Attempts to load the liblabjackusb.dylib for Mac OS X.
    """
    try:
        l = ctypes.CDLL("liblabjackusb.dylib", use_errno=True)
    except:
        #Try to load with full path.
        l = ctypes.CDLL("/usr/local/lib/liblabjackusb.dylib", use_errno=True)
    l.LJUSB_StreamTO.errcheck = errcheck
    l.LJUSB_Read.errcheck = errcheck
    return l

def _loadLibrary():
    """_loadLibrary()
    Returns a ctypes dll pointer to the library.
    """
    global _os_name
    global _use_ptr

    _os_name = "nt"
    try:
        wlib = None
        if sys.platform.startswith("win32"):
            #Windows detected
            wlib = ctypes.WinDLL("labjackud.dll")
        if sys.platform.startswith("cygwin"):
            #Cygwin detected. WinDLL not available, but CDLL seems to work.
            wlib = ctypes.CDLL("labjackud.dll")
        if wlib is not None:
            #eGetPtr may not be available on the UD driver version installed.
            _use_ptr = hasattr(wlib, "eGetPtr")
            return wlib
    except Exception:
        e = sys.exc_info()[1]
        raise LabJackException("Could not load labjackud driver. Ethernet connectivity availability only.\n\n    The error was: %s" % e)

    _os_name = "posix"
    addStr = "Exodriver"
    try:
        if sys.platform.startswith("linux"):
            #Linux detected
            addStr = "Linux SO"
            return _loadLinuxSo()
        if sys.platform.startswith("darwin"):
            #Mac detected
            addStr = "Mac Dylib"
            return _loadMacDylib()
        #Other OS? Just try to load the Exodriver like a Linux SO
        addStr = "Other SO"
        return _loadLinuxSo()
    except OSError:
        e = sys.exc_info()[1]
        raise LabJackException("Could not load the Exodriver driver. Ethernet connectivity only.\n\nCheck that the Exodriver is installed, and the permissions are set correctly.\nThe error message was: %s" % e)
    except Exception:
        e = sys.exc_info()[1]
        raise LabJackException("Could not load the %s for some reason other than it not being installed. Ethernet connectivity only.\n\n    The error was: %s" % (addStr, e))

try:
    staticLib = _loadLibrary()
except LabJackException:
    e = sys.exc_info()[1]
    print("%s: %s" % (type(e), e))
    staticLib = None


class Device(object):
    """Device(handle, localId = None, serialNumber = None, ipAddress = "", devType = None)
            
    Creates a simple 0 with the following functions:
    write(writeBuffer) -- Writes a buffer.
    writeRegister(addr, value) -- Writes a value to a modbus register
    read(numBytes) -- Reads until a packet is received.
    readRegister(addr, numReg = None, format = None) -- Reads a modbus register.
    ping() -- Pings the device.  Returns true if communication worked.
    close() -- Closes the device.
    reset() -- Resets the device.
    """
    def __init__(self, handle, localId = None, serialNumber = None, ipAddress = "", devType = None):
        # Not saving the handle as a void* causes many problems on 64-bit machines.
        if isinstance(handle, int):
            self.handle = ctypes.c_void_p(handle)
        else:
            self.handle = handle
        self.localId = localId
        self.serialNumber = serialNumber
        self.ipAddress = ipAddress
        self.devType = devType
        self.debug = False
        self.streamConfiged = False
        self.streamStarted = False
        self.streamPacketOffset = 0
        self._autoCloseSetup = False
        self.modbusPrependZeros = True
        self.deviceLock = threading.Lock()
        self.deviceName = "LabJack"
        

    def _writeToLJSocketHandle(self, writeBuffer, modbus):
        #if modbus is True and self.modbusPrependZeros:
        #        writeBuffer = [ 0, 0 ] + writeBuffer
            
        packFormat = "B" * len(writeBuffer)
        tempString = pack(packFormat, *writeBuffer)
        
        if modbus:
            self.handle.modbusSocket.send(tempString)
        else:
            self.handle.crSocket.send(tempString)
        
        return writeBuffer

    def _writeToUE9TCPHandle(self, writeBuffer, modbus):
        packFormat = "B" * len(writeBuffer)
        tempString = pack(packFormat, *writeBuffer)
        
        if modbus is True:
            if self.handle.modbus is None:
                raise LabJackException("Modbus port is not available.  Please upgrade to UE9 Comm firmware 1.43 or higher.")
            self.handle.modbus.send(tempString)
        else:
            self.handle.data.send(tempString)
        
        return writeBuffer

    def _writeToExodriver(self, writeBuffer, modbus):
        if modbus is True and self.modbusPrependZeros:
            writeBuffer = [ 0, 0 ] + writeBuffer
        
        newA = (ctypes.c_byte*len(writeBuffer))(0) 
        for i in range(len(writeBuffer)):
            newA[i] = ctypes.c_byte(writeBuffer[i])
        
        writeBytes = staticLib.LJUSB_Write(self.handle, ctypes.byref(newA), len(writeBuffer))
        
        if writeBytes != len(writeBuffer):
            raise LabJackException( "Could only write %s of %s bytes." % (writeBytes, len(writeBuffer) ) )
            
        return writeBuffer

    def _writeToUDDriver(self, writeBuffer, modbus):
        if modbus is True and self.devType == 9:
            dataWords = len(writeBuffer)
            writeBuffer = [0, 0xF8, 0, 0x07, 0, 0] + writeBuffer  # Modbus low-level function
            if dataWords % 2 != 0:
                dataWords = (dataWords+1) // 2
                writeBuffer.append(0)
            else:
                dataWords = dataWords // 2
            writeBuffer[2] = dataWords
            setChecksum(writeBuffer)
        elif modbus is True and self.modbusPrependZeros:
            writeBuffer = [0, 0] + writeBuffer

        eGetRaw(self.handle, LJ_ioRAW_OUT, 0, len(writeBuffer), writeBuffer)

        return writeBuffer

    def _debugprint(self, msg):
        """Conditionally output msg.
        
        If self.debug is a logging.Logger object, send the msg to it with
        DEBUG priority.  Otherwise, if self.debug is any truthy, just print
        it to stdout.
        """
        
        if self.debug:
            if isinstance(self.debug, logging.Logger):
                self.debug.debug(msg)
            else:
                print(msg)

    def write(self, writeBuffer, modbus = False, checksum = True):
        """write([writeBuffer], modbus = False)

        Writes the data contained in writeBuffer to the device.  writeBuffer must be a list of 
        byte values.
        """
        if self.handle is None:
            raise LabJackException("The device handle is None.")

        if checksum:
            setChecksum(writeBuffer)

        if isinstance(self.handle, LJSocketHandle):
            wb = self._writeToLJSocketHandle(writeBuffer, modbus)
        elif isinstance(self.handle, UE9TCPHandle):
            wb = self._writeToUE9TCPHandle(writeBuffer, modbus)
        else:
            if _os_name == 'posix':
                wb = self._writeToExodriver(writeBuffer, modbus)
            elif _os_name == 'nt':
                wb = self._writeToUDDriver(writeBuffer, modbus)
        
        self._debugprint("Sent: " + hexWithoutQuotes(wb))

    def read(self, numBytes, stream = False, modbus = False):
        """read(numBytes, stream = False, modbus = False)

        Blocking read until a packet is received. Returns a list of
        byte values when modbus is False. When modbus is true, returns
        a string in Python 2.x, or a bytes object in Python 3+.
        """
        if self.handle is None:
            raise LabJackException("The device handle is None.")

        result = []
        if isinstance(self.handle, LJSocketHandle):
            result = self._readFromLJSocketHandle(numBytes, modbus, stream)
        elif isinstance(self.handle, UE9TCPHandle):
            result = self._readFromUE9TCPHandle(numBytes, stream, modbus)
        else:
            if _os_name == 'posix':
                result = self._readFromExodriver(numBytes, stream, modbus)
            elif _os_name == 'nt':
                result = self._readFromUDDriver(numBytes, stream, modbus)

        return result

    def _readFromLJSocketHandle(self, numBytes, modbus, spont = False):
        """
        Reads from LJSocket. Returns the result as a list.
        """
        if modbus:
            rcvString = self.handle.modbusSocket.recv(numBytes)
        elif spont:
            rcvString = self.handle.spontSocket.recv(numBytes)
        else:
            rcvString = self.handle.crSocket.recv(numBytes)
        readBytes = len(rcvString)
        packFormat = "B" * readBytes
        rcvDataBuff = unpack(packFormat, rcvString)
        return list(rcvDataBuff)

    def _readFromUE9TCPHandle(self, numBytes, stream, modbus):
        if stream is True:
            rcvString = self.handle.stream.recv(numBytes)
            return rcvString
        else:
            if modbus is True:
                if self.handle.modbus is None:
                    raise LabJackException("Modbus port is not available.  Please upgrade to UE9 Comm firmware 1.43 or higher.")
                rcvString = self.handle.modbus.recv(numBytes)
            else:
                rcvString = self.handle.data.recv(numBytes)
        readBytes = len(rcvString)
        packFormat = "B" * readBytes
        rcvDataBuff = unpack(packFormat, rcvString)
        return list(rcvDataBuff)

    def _readFromExodriver(self, numBytes, stream, modbus):
        newA = (ctypes.c_byte*numBytes)()
        
        if stream:
            readBytes = staticLib.LJUSB_StreamTO(self.handle, ctypes.byref(newA), numBytes, 1500)
            if readBytes == 0:
                return ''
            # return the byte string in stream mode
            return pack('b' * readBytes, *newA)
        else:
            readBytes = staticLib.LJUSB_Read(self.handle, ctypes.byref(newA), numBytes)
            # return a list of integers in command/response mode
            return [(newA[i] & 0xff) for i in range(readBytes)]

    def _readFromUDDriver(self, numBytes, stream, modbus):
        if modbus is True and self.devType == 9:
            tempBuff = [0] * (8 + numBytes + numBytes%2)
            eGetBuff = list()
            eGetBuff = eGetRaw(self.handle, LJ_ioRAW_IN, 0, len(tempBuff), tempBuff)[1]

            # Parse the Modbus response out (response is the Modbus extended
            # low-level function)
            retBuff = list()
            if len(eGetBuff) >= 9 and eGetBuff[1] == 0xF8 and eGetBuff[3] == 0x07:
                # Figuring out the length of the Modbus response
                mbSize = len(eGetBuff) - 8
                if len(eGetBuff) >= 14:
                    mbSize = min(mbSize, eGetBuff[13] + 6)
                i = min(mbSize, numBytes)
                i = max(i, 0)
                retBuff = eGetBuff[8:8+i]  # Getting the response only
            return retBuff

        tempBuff = [0] * numBytes
        if stream:
            return eGetRaw(self.handle, LJ_ioRAW_IN, 1, numBytes, tempBuff)[1]
        return eGetRaw(self.handle, LJ_ioRAW_IN, 0, numBytes, tempBuff)[1]

    def readRegister(self, addr, numReg = None, format = None, unitId = None):
        """Reads a specific register from the device and returns the value.
        Requires Modbus.py

        readHoldingRegister(addr, numReg = None, format = None)
        addr: The address you would like to read
        numReg: Number of consecutive addresses you would like to read
        format: The unpack format of the returned value ( '>f' or '>I')

        Modbus is supported for UE9s over USB from Comm Firmware 1.50 and above.
        """
        pkt, numBytes = self._buildReadRegisterPacket(addr, numReg, unitId)
        response = self._modbusWriteRead(pkt, numBytes)
        return self._parseReadRegisterResponse(response, numBytes, addr, format, numReg)

    def _buildReadRegisterPacket(self, addr, numReg, unitId):
        """
        self._buildReadRegisterPacket(addr, numReg)

        Builds a raw modbus "Read Register" packet to be written to a device

        Returns a tuple:
        (<Packet as a list>, <number of bytes to read>)
        """
        # Calculates the number of registers for that request, or if numReg is
        # specified, checks that it is a valid number.
        numReg = Modbus.calcNumberOfRegisters(addr, numReg = numReg)
        pkt = toList(Modbus.readHoldingRegistersRequest(addr, numReg = numReg, unitId = unitId))
        numBytes = 9 + (2 * int(numReg))
        return (pkt, numBytes)

    def _parseReadRegisterResponse(self, response, numBytes, addr, format, numReg = None):
        """
        self._parseReadRegisterReponse(reponse, numBytes, addr, format)

        Takes a "Read Register" response and converts it to a value

        Returns the value.
        """
        if len(response) != numBytes:
            raise LabJackException(9001, "Got incorrect number of bytes from device. Expected %s bytes, got %s bytes. The packet recieved was: %s" % (numBytes, len(response), response))

        if isinstance(response, list):
            packFormat = ">" + "B" * numBytes
            response = pack(packFormat, *response)

        if format is None:
            format = Modbus.calcFormat(addr, numReg)

        value = Modbus.readHoldingRegistersResponse(response, payloadFormat=format)
        return value

    def writeRegister(self, addr, value, unitId = None):
        """
        Writes a value to a register. Returns the value to be written, if successful.
        Requires Modbus.py

        writeRegister(self, addr, value)
        addr: The address you want to write to.
        value: The value, or list of values, you want to write.

        If you cannot write to that register, a LabJackException is raised.
        Modbus is not supported for UE9s over USB. If you try it, a LabJackException is raised.
        """
        pkt, numBytes = self._buildWriteRegisterPacket(addr, value, unitId)
        response = self._modbusWriteRead(pkt, numBytes)
        return self._parseWriteRegisterResponse(response, pkt, value)

    def _buildWriteRegisterPacket(self, addr, value, unitId):
        """
        self._buildWriteRegisterPacket(addr, value)

        Builds a raw modbus "Write Register" packet to be written to a device.

        Returns a tuple:
        (<Packet as a list>, <number of bytes to read>)
        """
        if isinstance(value, list):
            return self._buildWriteMultipleRegisters(addr, value, unitId)

        fmt = Modbus.calcFormat(addr)
        if fmt != '>H':
            return self._buildWriteFloatToRegister(addr, value, unitId, fmt)

        request = toList(Modbus.writeRegisterRequest(addr, value, unitId))
        numBytes = 12
        return request, numBytes

    def _buildWriteFloatToRegister(self, addr, value, unitId, fmt = '>f'):
        if not isinstance(value, int) and not isinstance(value, float):
            raise TypeError("Value must be a float or int.")

        # Function, Address, Num Regs, Byte count, Data
        payload = pack('>BHHB', 0x10, addr, 0x02, 0x04) + pack(fmt, value)

        request = Modbus._buildHeaderBytes(length = len(payload)+1, unitId = unitId)
        request += payload
        request = toList(request)
        numBytes = 12
        return (request, numBytes)

    def _buildWriteMultipleRegisters(self, startAddr, values, unitId = None):
        request = toList(Modbus.writeRegistersRequest(startAddr, values, unitId))
        numBytes = 12
        return (request, numBytes)

    def _parseWriteRegisterResponse(self, response, request, value):
        response = list(response)

        if request[2] != 0 and request[3] != 0:
            protoID = (request[2] << 8) + request[3]
            raise Modbus.ModbusException("Got an unexpected protocol ID: %s (expected 0). Please make sure that you have the latest firmware. UE9s need Comm Firmware of 1.50 or greater.\n\nThe packet you received: %s" % (protoID, hexWithoutQuotes(response)))

        if request[7] != response[7]:
            raise LabJackException(9002, "Modbus error number %s raised while writing to register. Make sure you're writing to an address that allows writes.\n\nThe packet you received: %s" % (response[8], hexWithoutQuotes(response)))

        return value

    def setDIOState(self, IOnum, state):
        value = (int(state) & 0x01)
        self.writeRegister(6000+IOnum, value)
        return True

    def _modbusWriteRead(self, request, numBytes):
        with self.deviceLock:
            self.write(request, modbus = True, checksum = False)
            try:
                result = self.read(numBytes, modbus = True)
                self._debugprint("Response: " + hexWithoutQuotes(result))
                return result
            except LabJackException:
                self.write(request, modbus = True, checksum = False)
                result = self.read(numBytes, modbus = True)
                self._debugprint("Response: " + hexWithoutQuotes(result))
                return result

    def _checkCommandBytes(self, results, commandBytes):
        """
        Checks all the stuff from a command
        """
        size = len(commandBytes)
        if len(results) == 0:
            raise LabJackException("Got a zero length packet.")
        elif results[0] == 0xB8 and results[1] == 0xB8:
            raise LabJackException("Device detected a bad checksum.")
        elif results[1:(size+1)] != commandBytes:
            raise LabJackException("Got incorrect command bytes.\nExpected: %s\nGot: %s\nFull packet: %s" % (hexWithoutQuotes(commandBytes), hexWithoutQuotes(results[1:(size+1)]), hexWithoutQuotes(results)))
        elif not verifyChecksum(results):
            raise LabJackException("Checksum was incorrect.")
        elif results[6] != 0:
            raise LowlevelErrorException(results[6], "\nThe %s returned an error:\n    %s" % (self.deviceName , lowlevelErrorToString(results[6])) )
    
    def _writeRead(self, command, readLen, commandBytes, checkBytes = True, stream=False, checksum = True):
    
        # Acquire the device lock.
        with self.deviceLock:
            self.write(command, checksum = checksum)
            
            result = self.read(readLen, stream=False)
            self._debugprint("Response: " + hexWithoutQuotes(result))
            if checkBytes:
                self._checkCommandBytes(result, commandBytes)
                        
            return result
    
    
    def ping(self):
        try:
            if self.devType == LJ_dtUE9:
                writeBuffer = [0x70, 0x70]
                self.write(writeBuffer)
                try:
                    self.read(2)
                except LabJackException:
                    self.write(writeBuffer)
                    self.read(2)
                return True
            
            if self.devType == LJ_dtU3:
                writeBuffer = [0, 0xf8, 0x01, 0x2a, 0, 0, 0, 0]
                writeBuffer = setChecksum(writeBuffer)
                self.write(writeBuffer)
                self.read(40)
                return True

            return False
        except Exception:
            e = sys.exc_info()[1]
            print(e)
            return False
        

    def open(self, devType, Ethernet=False, firstFound = True, serial = None, localId = None, devNumber = None, ipAddress = None, handleOnly = False, LJSocket = None):
        """
        Device.open(devType, Ethernet=False, firstFound = True, serial = None, localId = None, devNumber = None, ipAddress = None, handleOnly = False, LJSocket = None)
        
        Open a device of type devType. 
        """
        
        if self.handle is not None:
            raise LabJackException(9000,"Open called on a device with a handle. Please close the device, and try again. Your device is probably already open.\nLook for lines of code that look like this:\nd = u3.U3()\nd.open() # Wrong! Device is already open.")
        
        ct = LJ_ctUSB
        
        if Ethernet:
            ct = LJ_ctETHERNET
        
        if LJSocket is not None:
            ct = LJ_ctLJSOCKET
        
        d = None
        if devNumber:
            d = openLabJack(devType, ct, firstFound = False, devNumber = devNumber, handleOnly = handleOnly, LJSocket = LJSocket)
        elif serial:
            d = openLabJack(devType, ct, firstFound = False, pAddress = serial, handleOnly = handleOnly, LJSocket = LJSocket)
        elif localId:
            d = openLabJack(devType, ct, firstFound = False, pAddress = localId, handleOnly = handleOnly, LJSocket = LJSocket)
        elif ipAddress:
            d = openLabJack(devType, ct, firstFound = False, pAddress = ipAddress, handleOnly = handleOnly, LJSocket = LJSocket)
        elif LJSocket:
            d = openLabJack(devType, ct, handleOnly = handleOnly, LJSocket = LJSocket)
        elif firstFound:
            d = openLabJack(devType, ct, firstFound = True, handleOnly = handleOnly, LJSocket = LJSocket)
        else:
            raise LabJackException("You must use first found, or give a localId, devNumber, or IP Address")
        
        self.handle = d.handle
        
        if not handleOnly:
            self._loadChangedIntoSelf(d)
            
        self._registerAtExitClose()
                    

    def _loadChangedIntoSelf(self, d):
        for key, value in d.changed.items():
            self.__setattr__(key, value)
            
    def _registerAtExitClose(self):
        if not self._autoCloseSetup:
            # Only need to register auto-close once per device.
            atexit.register(self.close)
            self._autoCloseSetup = True

    def close(self):
        """
        close()

        This function is not specifically supported in the LabJackUD driver
        for Windows and so simply calls the UD function Close.  For Mac and unix
        drivers, this function MUST be performed when finished with a device.
        The reason for this close is because there can not be more than one program
        with a given device open at a time.  If a device is not closed before
        the program is finished it may still be held open and unable to be used
        by other programs until properly closed.

        For Windows, Linux, and Mac
        """
        if isinstance(self.handle, UE9TCPHandle) or isinstance(self.handle, LJSocketHandle):
            self.handle.close()
        elif _os_name == 'posix':
            staticLib.LJUSB_CloseDevice(self.handle)

        self.handle = None

    def reset(self):
        """
        Reset the LabJack device.

        For Windows, Linux, and Mac
    
        Sample Usage:
    
        >>> d = ue9.UE9()
        >>> d.reset()

        @type  None
        @param Function takes no arguments
        
        @rtype: None
        @return: Function returns nothing.
            
        @raise LabJackException:
        """
        if _os_name == 'nt':
            ec = staticLib.ResetLabJack(self.handle)
    
            if ec != 0: raise LabJackException(ec)
        elif _os_name == 'posix':
            sndDataBuff = [0] * 4

            #Make the reset packet
            sndDataBuff[0] = 0x9C #Checksum
            sndDataBuff[1] = 0x99
            sndDataBuff[2] = 0x03
            
            try:
                self._writeRead(sndDataBuff, 4, [], False, False, False)
            except Exception:
                e = sys.exc_info()[1]
                raise LabJackException(0, "Unable to reset labjack: %s" % str(e))

    def breakupPackets(self, packets, numBytesPerPacket):
        """
        Name: Device.breakupPackets
        Args: packets, a string or list of packets
              numBytesPerPacket, how big each packe is
        Desc: This function will break up a list into smaller chunks and return
              each chunk one at a time.

        >>> l = range(15)
        >>> for packet in d.breakupPackets(l, 5):
        ...     print(packet)
        [ 0, 1, 2, 3, 4 ]
        [ 5, 6, 7, 8, 9 ]
        [ 10, 11, 12, 13, 14]
        """
        start, end = 0, numBytesPerPacket
        while end <= len(packets):
            yield packets[start:end]
            start, end = end, end + numBytesPerPacket

    def samplesFromPacket(self, packet):
        """
        Name: Device.samplesFromPacket
        Args: packet, a packet of stream data
        Desc: This function breaks a packet into all the two byte samples it
              contains and returns them one at a time.
        
        >>> packet = range(16) # fake packet with 1 sample in it
        >>> for sample in d.samplesFromPacket(packet):
        ...     print(sample)
        [ 12, 13 ]
        """
        HEADER_SIZE = 12
        FOOTER_SIZE = 2
        BYTES_PER_PACKET = 2
        l = packet[HEADER_SIZE:-FOOTER_SIZE]
        for i in range(0, len(l), BYTES_PER_PACKET):
            yield l[i:i+BYTES_PER_PACKET]

    def streamStart(self):
        """
        Name: Device.streamStart()
        Args: None
        Desc: Starts streaming on the device.
        Note: You must call streamConfig() before calling this function.
        """
        if not self.streamConfiged:
            raise LabJackException("Stream must be configured before it can be started.")

        if self.streamStarted:
            raise LabJackException("Stream already started.")

        command = [0xA8, 0xA8]
        results = self._writeRead(command, 4, [], False, False, False)

        if results[2] != 0:
            raise LowlevelErrorException(results[2], "StreamStart returned an error:\n    %s" % lowlevelErrorToString(results[2]))

        self.streamPacketOffset = 0
        self.streamStarted = True

    def streamData(self, convert=True):
        """
        Name: Device.streamData()
        Args: convert, should the packets be converted as they are read.
                       set to False to get much faster speeds, but you will
                       have to process the results later.
        Desc: Reads stream data from a LabJack device. See our stream example
              to get an idea of how this function should be called. The return
              value of streamData is a dictionary with the following keys:
              * errors: The number of errors in this block.
              * numPackets: The number of USB packets collected to return this
                            block.
              * missed: The number of readings that were missed because of
                        buffer overflow on the LabJack.
              * firstPacket: The PacketCounter value in the first USB packet.
              * result: The raw bytes returned from read(). The only way to get
                        data if called with convert = False. In Python 2 this
                        is a string, and in Python 3+ is a bytes object.
              * AINi, where i is an entry in the passed in PChannels. If called
                        with convert = True, this is a list of all the readings
                        in this block.
        Note: You must start the stream by calling streamStart() before calling
              this function.
        """
        if not self.streamStarted:
            raise LabJackException("Please start streaming before reading.")

        numBytes = 14 + (self.streamSamplesPerPacket * 2)
        while True:
            result = self.read(numBytes * self.packetsPerRequest, stream = True)

            if len(result) == 0:
                yield None
                continue

            numPackets = len(result) // numBytes

            errors = 0
            missed = 0
            firstPacket = streamByteToInt(result[10])
            for i in range(numPackets):
                e = streamByteToInt(result[11+(i*numBytes)])
                if e != 0:
                    errors += 1
                    if e != 60 and e != 59:
                        self._debugprint(e)
                    if e == 60:
                        missed += unpack('<I', result[6+(i*numBytes):10+(i*numBytes)])[0]

            returnDict = dict(numPackets = numPackets, result = result, errors = errors, missed = missed, firstPacket = firstPacket)

            if convert:
                returnDict.update(self.processStreamData(result, numBytes = numBytes))

            yield returnDict

    def streamStop(self):
        """
        Name: Device.streamStop()
        Args: None
        Desc: Stops streaming on the device.
        """
        command = [0xB0, 0xB0]
        results = self._writeRead(command, 4, [], False, False, False)

        if results[2] != 0:
            raise LowlevelErrorException(results[2], "StreamStop returned an error:\n    %s" % lowlevelErrorToString(results[2]))

        self.streamStarted = False

    def getName(self):
        """
        Name: Device.getName()
        Args: None
        Desc: Returns the name of a device.
              Always returns a unicode string.
              Works as of the following firmware versions:
              U6 - 1.00
              U3 - 1.22
              UE9 - 2.00
        
        >>> d = u3.U3()
        >>> d.open()
        >>> d.getName()
        u'My LabJack U3'
        """
        name = list(self.readRegister(58000, format='B'*48, numReg = 24))
        
        if name[1] == 3:
            # Old style string
            name = "My %s" % self.deviceName
            self._debugprint("Old UTF-16 name detected, replacing with %s" % name)
            self.setName(name)
            name = name.decode("UTF-8")
        else:
            try:
                end = name.index(0x00)
                name = pack("B"*end, *name[:end]).decode("UTF-8")
            except ValueError:
                name = "My %s" % self.deviceName
                self._debugprint("Invalid name detected, replacing with %s" % name)
                self.setName(name)
                name = name.decode("UTF-8")
        
        return name
        
    def setName(self, name = "My LabJack U3"):
        """
        Name: Device.setName(name = "My LabJack U3")
        Args: name, the name you'd like to assign the the U3
        Desc: Writes a new name to the device.
              Names a limited to 30 characters or less.
              Works as of the following firmware versions:
              U6 - 1.00
              U3 - 1.22
              UE9 - 2.00
        
        >>> d = u3.U3()
        >>> d.open()
        >>> d.getName()
        u'My LabJack U3'
        >>> d.setName("Johann")
        >>> d.getName()
        u'Johann'
        """
        strLen = len(name)
        
        if strLen > 47:
            raise LabJackException("The name is too long, must be less than 48 characters.")
        
        newname = name.encode('UTF-8')
        bl = list(unpack("B"*strLen, newname)) + [0x00]
        strLen += 1
        
        if strLen%2 != 0:
            bl = bl + [0x00]
            strLen += 1
        
        bl = unpack(">"+"H"*(strLen/2), pack("B" * strLen, *bl))
        
        self.writeRegister(58000, list(bl))

    name = property(getName, setName)

    def setDefaults(self, SetToFactoryDefaults = False):
        """
        Name: Device.setDefaults(SetToFactoryDefaults = False)
        Args: SetToFactoryDefaults, set to True reset to factory defaults.
        Desc: Executing this function causes the current or last used values
              (or the factory defaults) to be stored in flash as the power-up
              defaults.
        
        >>> myU6 = U6()
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
    def readDefaults(self, BlockNum, ReadCurrent = False):
        """
        Name: Device.readDefaults(BlockNum)
        Args: BlockNum, which block to read. Must be 0-7.
              ReadCurrent, True = read current configuration
        Desc: Reads the power-up defaults from flash.
        
        >>> myU6 = U6()
        >>> myU6.readDefaults(0)
        [ 0, 0, ... , 0]        
        """
        if BlockNum not in self.validDefaultBlocks:
            raise LabJackException("Defaults must be in range 0-7")
        
        byte7 = (int(bool(ReadCurrent)) << 7) + BlockNum
        
        command = [ 0, 0xF8, 0x01, 0x0E, 0, 0, 0, byte7 ]
        
        result = self._writeRead(command, 40, [ 0xF8, 0x11, 0x0E ])
        
        return result[8:]
        
    def readCurrent(self, BlockNum):
        self.readDefaults(BlockNum, ReadCurrent = True)
        
    def loadGenericDevice(self, device):
        """ Take a generic Device object, and loads it into the current object.
            The generic Device is consumed in the process.
        """
        self.handle = device.handle
        
        self._loadChangedIntoSelf(device)
        
        self._registerAtExitClose()
        
        device = None

# --------------------- BEGIN LabJackPython ---------------------------------

def setChecksum(command):
    """Returns a command with checksums places in the proper locations

    For Windows, Mac, and Linux
    
    Sample Usage:
    
    >>> from LabJackPython import setChecksum
    >>> command = [0] * 12
    >>> command[1] = 0xf8
    >>> command[2] = 0x03
    >>> command[3] = 0x0b
    >>> command = setChecksum(command)
    >>> command
    [7, 248, 3, 11, 0, 0, 0, 0, 0, 0, 0, 0]

    @type  command: List
    @param command: The command by which to calculate the checksum

    @rtype: List
    @return: A command list with checksums in the proper locations.
    """  
    
    if len(command) < 6:
        raise LabJackException("Command does not contain enough bytes.")
    
    try:        
        a = command[1]
        
        a = (a & 0x78) >> 3
        
        #Check if the command is an extended command
        if a == 15:
            command = setChecksum16(command)
            command = setChecksum8(command, 6)
            return command
        else:
            command = setChecksum8(command, len(command))
            return command
    except LabJackException:
        e = sys.exc_info()[1]
        raise e
    except Exception:
        e = sys.exc_info()[1]
        raise LabJackException("SetChecksum Exception:" + str(e))



def verifyChecksum(buffer):
    """Verifies the checksum of a given buffer using the traditional U3/UE9 Command Structure.
    """
    
    buff0 = buffer[0]
    buff4 = buffer[4]
    buff5 = buffer[5]

    tempBuffer = setChecksum(buffer)
    
    if (buff0 == tempBuffer[0]) and (buff4 == tempBuffer[4]) \
    and (buff5 == tempBuffer[5]):
        return True

    return False

# 1 = LJ_ctUSB
def listAll(deviceType, connectionType = 1):
    """listAll(deviceType, connectionType) -> [[local ID, Serial Number, IP Address], ...]

    Searches for all devices of a given type over a given connection
    type and returns a list of all devices found.

    WORKS on WINDOWS, MAC, UNIX
    """
    if connectionType == LJ_ctLJSOCKET:
        ipAddress, port = deviceType.split(":")
        port = int(port)

        serverSocket = socket.socket()
        serverSocket.connect((ipAddress, port))
        serverSocket.settimeout(10)

        f = serverSocket.makefile(bufsize = 0)
        f.write("scan\r\n")

        l = f.readline().strip()
        try:
            status, numLines = l.split(' ')
        except ValueError:
            raise Exception("Got invalid line from server: %s" % l)

        if status.lower().startswith('ok'):
            lines = []
            for i in range(int(numLines)):
                l = f.readline().strip()
                dev = parseline(l)
                lines.append(dev)

            f.close()
            serverSocket.close()

            return lines

    if deviceType == 12:
        if U12DriverPresent():
            if sys.platform.startswith("cygwin"):
                u12Driver = ctypes.cdll.LoadLibrary("ljackuw")
            else:
                u12Driver = ctypes.windll.LoadLibrary("ljackuw")

            # Setup all the ctype arrays
            pSerialNumbers = (ctypes.c_long * 127)(0)
            pIDs = (ctypes.c_long * 127)(0)
            pProdID = (ctypes.c_long * 127)(0)
            pPowerList = (ctypes.c_long * 127)(0)
            pCalMatrix = (ctypes.c_long * 2540)(0)
            pNumFound = ctypes.c_long()
            pFcdd = ctypes.c_long(0)
            pHvc = ctypes.c_long(0)

            # Output dictionary
            deviceList = {}

            ec = u12Driver.ListAll(ctypes.cast(pProdID, ctypes.POINTER(ctypes.c_long)),
                               ctypes.cast(pSerialNumbers, ctypes.POINTER(ctypes.c_long)),
                               ctypes.cast(pIDs, ctypes.POINTER(ctypes.c_long)),
                               ctypes.cast(pPowerList, ctypes.POINTER(ctypes.c_long)),
                               ctypes.cast(pCalMatrix, ctypes.POINTER(ctypes.c_long)),
                               ctypes.byref(pNumFound),
                               ctypes.byref(pFcdd),
                               ctypes.byref(pHvc))
            if ec != 0:
                raise LabJackException(ec)

            for i in range(pNumFound.value):
                deviceList[pSerialNumbers[i]] = {'SerialNumber': pSerialNumbers[i], 'Id': pIDs[i], 'ProdId': pProdID[i], 'powerList': pPowerList[i]}

            return deviceList
        else:
            return {}

    if _os_name == 'nt':
        pNumFound = ctypes.c_long()
        pSerialNumbers = (ctypes.c_long * 128)()
        pIDs = (ctypes.c_long * 128)()
        pAddresses = (ctypes.c_double * 128)()

        ec = staticLib.ListAll(deviceType, connectionType,
                              ctypes.byref(pNumFound),
                              ctypes.cast(pSerialNumbers, ctypes.POINTER(ctypes.c_long)),
                              ctypes.cast(pIDs, ctypes.POINTER(ctypes.c_long)), 
                              ctypes.cast(pAddresses, ctypes.POINTER(ctypes.c_long)))
        if ec != 0 and ec != 1010:
            raise LabJackException(ec)

        deviceList = dict()
        for i in range(pNumFound.value):
            if pSerialNumbers[i] != 1010:
                deviceValue = dict(localId = pIDs[i], serialNumber = pSerialNumbers[i], ipAddress = DoubleToStringAddress(pAddresses[i]), devType = deviceType)
                deviceList[pSerialNumbers[i]] = deviceValue
        return deviceList

    if _os_name == 'posix':
        if deviceType == LJ_dtUE9:
            return __listAllUE9Unix(connectionType)
        if deviceType == LJ_dtU3:
            return __listAllU3Unix()
        if deviceType == 6:
            return __listAllU6Unix()

def isHandleValid(handle):
    if _os_name == 'nt':
        return True
    else:
        return staticLib.LJUSB_IsHandleValid(handle)

def deviceCount(devType = None):
    """Returns the number of devices connected."""
    if _os_name == 'nt':
        if devType is None:
            numdev = len(listAll(3))
            numdev += len(listAll(9))
            numdev += len(listAll(6))
            return numdev
        else:
            return len(listAll(devType))
    else:
        if devType is None:
            numdev = staticLib.LJUSB_GetDevCount(3)
            numdev += staticLib.LJUSB_GetDevCount(9)
            numdev += staticLib.LJUSB_GetDevCount(6)
            return numdev
        else:
            return staticLib.LJUSB_GetDevCount(devType)

def getDevCounts():
    if _os_name == "nt":
        # Right now there is no good way to count all the U12s on a Windows box
        returnDict = {3: len(listAll(3)), 6: len(listAll(6)), 9: len(listAll(9)), 1: 0}
        return returnDict
    else:
        devCounts = (ctypes.c_uint*NUMBER_OF_UNIQUE_LABJACK_PRODUCT_IDS)()
        devIds = (ctypes.c_uint*NUMBER_OF_UNIQUE_LABJACK_PRODUCT_IDS)()
        n = ctypes.c_uint(NUMBER_OF_UNIQUE_LABJACK_PRODUCT_IDS)
        staticLib.LJUSB_GetDevCounts(ctypes.byref(devCounts), ctypes.byref(devIds), n)

        returnDict = dict()

        for i in range(NUMBER_OF_UNIQUE_LABJACK_PRODUCT_IDS):
            returnDict[int(devIds[i])] = int(devCounts[i])

        return returnDict

def openAllLabJacks():
    if _os_name == "nt":
        # Windows doesn't provide a nice way to open all the devices.
        devs = dict()
        devs[3] = listAll(3)
        devs[6] = listAll(6)
        devs[9] = listAll(9)
        devices = list()
        for prodId, numConnected in devs.items():
            for i, serial in enumerate(numConnected.keys()):
                d = Device(None, devType = prodId)
                d.open(prodId, serial = serial)
                d = _makeDeviceFromHandle(d.handle, prodId)
                devices.append(d)
    else:
        maxHandles = 10
        devHandles = (ctypes.c_void_p*maxHandles)()
        devIds = (ctypes.c_uint*maxHandles)()
        n = ctypes.c_uint(maxHandles)
        numOpened = staticLib.LJUSB_OpenAllDevices(ctypes.byref(devHandles), ctypes.byref(devIds), n)

        devices = list()
        for i in range(numOpened):
            devices.append(_makeDeviceFromHandle(devHandles[i], int(devIds[i])))

    return devices

def _openLabJackUsingLJSocket(deviceType, firstFound, pAddress, LJSocket, handleOnly):
    if LJSocket is not None and LJSocket != '':
        ip, port = LJSocket.split(":")
        port = int(port)
        handle = LJSocketHandle(ip, port, deviceType, firstFound, pAddress)
    else:
        handle = LJSocketHandle('localhost', 6000, deviceType, firstFound, pAddress)

    return handle

def _openLabJackUsingUDDriver(deviceType, connectionType, firstFound, pAddress, devNumber):
    if devNumber is not None:
        devs = listAll(deviceType)
        pAddress = list(devs.keys())[devNumber-1]

    handle = ctypes.c_long()
    pAddress = str(pAddress).encode("ascii")
    ec = staticLib.OpenLabJack(deviceType, connectionType,
                                pAddress, firstFound, ctypes.byref(handle))

    # Error codes > 0 are errors, < 0 are warnings and 0 is no error.
    # Warnings return a valid device handle.
    if ec > 0:
        raise LabJackException(ec)
    if ec < 0:
        print("Warning: " + str(LabJackException(ec)))

    devHandle = handle.value

    return devHandle

def _isOpenAccessError():
    """Returns True if no access/claim errno detected after device open,
    otherwise False. Use imediately after openDev if it returns a Null
    handle.
    """
    err = ctypes.get_errno()
    if err == errno.EBUSY or err == errno.EACCES:
        return True
    else:
        return False

def _openLabJackUsingExodriver(deviceType, firstFound, pAddress, devNumber):
    devType = ctypes.c_ulong(deviceType)
    openDev = staticLib.LJUSB_OpenDevice
    openDev.restype = ctypes.c_void_p

    accessInfoPart = "is not already open in another or the current process"
    accessInfoFull = "Device access or claim error. Please check that the device " + accessInfoPart + "."
    info = None

    if devNumber is not None:
        handle = openDev(devNumber, 0, devType)
        if handle is None or handle <= 0:
            if _isOpenAccessError():
                info = accessInfoFull
            raise NullHandleException(info)
        return handle
    elif firstFound:
        handle = openDev(1, 0, devType)
        if handle is None or handle <= 0:
            if _isOpenAccessError():
                info = accessInfoFull
            raise NullHandleException(info)
        return handle
    else:
        numDevices = staticLib.LJUSB_GetDevCount(deviceType)

        noAccessDetected = False
        for i in range(numDevices):
            handle = openDev(i + 1, 0, devType)
            try:
                if handle is None or handle <= 0:
                    if _isOpenAccessError():
                        noAccessDetected = True
                    raise NullHandleException()
                device = _makeDeviceFromHandle(handle, deviceType)
            except:
                continue

            if device.localId == pAddress or device.serialNumber == pAddress or device.ipAddress == pAddress:
                return device
            else:
                device.close()

        info = "Please check that the device you are trying to open is connected"
        if noAccessDetected:
            info += ", or " + accessInfoPart
        info += "."
        raise LabJackException(LJE_LABJACK_NOT_FOUND, "Couldn't open device. " + info)

    raise LabJackException(LJE_LABJACK_NOT_FOUND)

def _openUE9OverEthernet(firstFound, pAddress, devNumber):
    if firstFound is not True and pAddress is not None:
        #Check if valid IP address and attempt to get TCP handle
        try:
            socket.inet_aton(pAddress)
            return UE9TCPHandle(pAddress)
        except:
            pass

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(BROADCAST_SOCKET_TIMEOUT)

    sndDataBuff = [0] * 6
    sndDataBuff[0] = 0x22
    sndDataBuff[1] = 0x78
    sndDataBuff[3] = 0xa9

    outBuff = ""
    for item in sndDataBuff:
        outBuff += chr(item)
    s.sendto(outBuff, ("255.255.255.255", 52362))

    try:
        count = 1
        while True:
            rcvDataBuff = s.recv(128)
            rcvDataBuff = [ord(val) for val in rcvDataBuff]
            if verifyChecksum(rcvDataBuff):
                #Parse the packet
                macAddress = rcvDataBuff[28:34]
                macAddress.reverse()

                # The serial number is four bytes:
                # 0x10 and the last three bytes of the MAC address
                serialBytes = chr(0x10)
                for j in macAddress[3:]:
                    serialBytes += chr(j)
                serialNumber = unpack(">I", serialBytes)[0]

                #Parse out the IP address
                ipAddress = ""
                for j in range(13, 9, -1):
                    ipAddress += str(int(rcvDataBuff[j]))
                    ipAddress += "." 
                ipAddress = ipAddress[0:-1]

                #Local ID
                localId = rcvDataBuff[8] & 0xff
                
                # Check if we have found the device we are looking for.
                # pAddress represents either Local ID, Serial Number, or the
                # IP Address. This is so there are no conflicting identifiers.
                if firstFound \
                or devNumber == count \
                or pAddress in [localId, serialNumber, ipAddress]:
                    handle = UE9TCPHandle(ipAddress)
                    return handle
                
                count += 1
            else:
                # Got a bad checksum.
                pass
    except LabJackException:
        e = sys.exc_info()[1]
        raise LabJackException(LJE_LABJACK_NOT_FOUND, "%s" % e)
    except:
        raise LabJackException("LJE_LABJACK_NOT_FOUND: Couldn't find the specified LabJack.")

#Windows, Linux, and Mac
def openLabJack(deviceType, connectionType, firstFound = True, pAddress = None, devNumber = None, handleOnly = False, LJSocket = None):
    """openLabJack(deviceType, connectionType, firstFound = True, pAddress = 1, LJSocket = None)

    Note: On Windows, UE9 over Ethernet, pAddress MUST be the IP address. 
    """
    handle = None

    if connectionType == LJ_ctLJSOCKET:
        # LJSocket handles work independent of OS
        handle = _openLabJackUsingLJSocket(deviceType, firstFound, pAddress, LJSocket, handleOnly)
    elif _os_name == 'posix' and connectionType == LJ_ctUSB:
        # Using Exodriver on Linux/Mac for USB connections.
        handle = _openLabJackUsingExodriver(deviceType, firstFound, pAddress, devNumber)
        if isinstance(handle, Device):
            return handle
    elif _os_name == 'nt':
        # Using UD driver on Windows.
        handle = _openLabJackUsingUDDriver(deviceType, connectionType, firstFound, pAddress, devNumber)
    elif connectionType == LJ_ctETHERNET and deviceType == LJ_dtUE9:
        handle = _openUE9OverEthernet(firstFound, pAddress, devNumber)

    if not handleOnly:
        return _makeDeviceFromHandle(handle, deviceType)
    else:
        return Device(handle, devType = deviceType)

def _makeDeviceFromHandle(handle, deviceType):
    """ A helper function to get set all the info about a device from a handle"""
    device = Device(handle, devType = deviceType)
    device.changed = dict()

    if deviceType == LJ_dtUE9:
        sndDataBuff = [0] * 38
        sndDataBuff[0] = 0x89
        sndDataBuff[1] = 0x78
        sndDataBuff[2] = 0x10
        sndDataBuff[3] = 0x01

        try:
            device.write(sndDataBuff, checksum = False)
            rcvDataBuff = device.read(38)

            device.localId = rcvDataBuff[8] & 0xff
            device.ipAddress = "%s.%s.%s.%s" % (rcvDataBuff[13], rcvDataBuff[12], rcvDataBuff[11], rcvDataBuff[10])
            device.serialNumber = unpack("<I", pack("BBBB", rcvDataBuff[28], rcvDataBuff[29], rcvDataBuff[30], 0x10))[0]
            device.macAddress = "%02X:%02X:%02X:%02X:%02X:%02X" % (rcvDataBuff[33], rcvDataBuff[32], rcvDataBuff[31], rcvDataBuff[30], rcvDataBuff[29], rcvDataBuff[28])
            device.hwVersion = "%s.%02d" % (rcvDataBuff[35], rcvDataBuff[34])
            device.commFWVersion = "%s.%02d" % (rcvDataBuff[37], rcvDataBuff[36])

            device.changed['localId'] = device.localId
            device.changed['ipAddress'] = device.ipAddress
            device.changed['serialNumber'] = device.serialNumber
            device.changed['macAddress'] = device.macAddress
            device.changed['hwVersion'] = device.hwVersion
            device.changed['commFWVersion'] = device.commFWVersion
        except Exception:
            e = sys.exc_info()[1]
            device.close()
            raise e

        sndDataBuff = [0] * 18
        sndDataBuff[0] = 0x07
        sndDataBuff[1] = 0xF8
        sndDataBuff[2] = 0x06
        sndDataBuff[3] = 0x08

        try:
            device.write(sndDataBuff, checksum = False)
            rcvDataBuff = device.read(24)

            device.powerLevel = rcvDataBuff[7]
            device.controlFWVersion = "%s.%02d" % (rcvDataBuff[10], rcvDataBuff[9])
            device.controlBLVersion = "%s.%02d" % (rcvDataBuff[12], rcvDataBuff[11])
            device.hiRes = bool(rcvDataBuff[13] & 1)
            device.deviceName = 'UE9'
            if device.hiRes:
                device.deviceName = 'UE9-Pro'

            device.changed['powerLevel'] = device.powerLevel
            device.changed['controlFWVersion'] = device.controlFWVersion
            device.changed['controlBLVersion'] = device.controlBLVersion
            device.changed['hiRes'] = device.hiRes
            device.changed['deviceName'] = device.deviceName
        except Exception:
            e = sys.exc_info()[1]
            device.close()
            raise e
    elif deviceType == LJ_dtU3:
        sndDataBuff = [0] * 26
        sndDataBuff[0] = 0x0b
        sndDataBuff[1] = 0xf8
        sndDataBuff[2] = 0x0a
        sndDataBuff[3] = 0x08
        try:
            device.write(sndDataBuff, checksum = False)
            rcvDataBuff = device.read(38)
        except LabJackException:
            e = sys.exc_info()[1]
            device.close()
            raise e

        device.localId = rcvDataBuff[21] & 0xff
        serialNumber = pack("<BBBB", *rcvDataBuff[15:19])
        device.serialNumber = unpack('<I', serialNumber)[0]
        device.ipAddress = ""
        device.firmwareVersion = "%d.%02d" % (rcvDataBuff[10], rcvDataBuff[9])
        device.bootloaderVersion = "%s.%02d" % (rcvDataBuff[12], rcvDataBuff[11])
        device.hardwareVersion = "%d.%02d" % (rcvDataBuff[14], rcvDataBuff[13])
        device.versionInfo = rcvDataBuff[37]
        device.deviceName = 'U3'
        device.isHV = False
        if device.versionInfo == 1:
            device.deviceName += 'B'
        elif device.versionInfo == 2:
            device.deviceName += '-LV'
        elif device.versionInfo == 18:
            device.deviceName += '-HV'
            device.isHV = True

        device.changed['localId'] = device.localId
        device.changed['serialNumber'] = device.serialNumber
        device.changed['ipAddress'] = device.ipAddress
        device.changed['firmwareVersion'] = device.firmwareVersion
        device.changed['versionInfo'] = device.versionInfo
        device.changed['deviceName'] = device.deviceName
        device.changed['isHV'] = device.isHV
        device.changed['hardwareVersion'] = device.hardwareVersion
        device.changed['bootloaderVersion'] = device.bootloaderVersion
    elif deviceType == 6:
        command = [ 0 ] * 26
        command[1] = 0xF8
        command[2] = 0x0A
        command[3] = 0x08
        try:
            device.write(command)
            rcvDataBuff = device.read(38)
        except LabJackException:
            e = sys.exc_info()[1]
            device.close()
            raise e

        device.localId = rcvDataBuff[21] & 0xff
        serialNumber = pack("<BBBB", *rcvDataBuff[15:19])
        device.serialNumber = unpack('<I', serialNumber)[0]
        device.ipAddress = ""

        device.firmwareVersion = "%s.%02d" % (rcvDataBuff[10], rcvDataBuff[9])
        device.bootloaderVersion = "%s.%02d" % (rcvDataBuff[12], rcvDataBuff[11])
        device.hardwareVersion = "%s.%02d" % (rcvDataBuff[14], rcvDataBuff[13])
        device.versionInfo = rcvDataBuff[37]
        device.deviceName = 'U6'
        device.isPro = False
        if device.versionInfo == 12:
            device.deviceName = 'U6-Pro'
            device.isPro = True

        device.changed['localId'] = device.localId
        device.changed['serialNumber'] = device.serialNumber
        device.changed['ipAddress'] = device.ipAddress
        device.changed['firmwareVersion'] = device.firmwareVersion
        device.changed['versionInfo'] = device.versionInfo
        device.changed['deviceName'] = device.deviceName
        device.changed['isPro'] = device.isPro
        device.changed['hardwareVersion'] = device.hardwareVersion
        device.changed['bootloaderVersion'] = device.bootloaderVersion

    return device

#Windows
def AddRequest(Handle, IOType, Channel, Value, x1, UserData):
    """AddRequest(handle, ioType, channel, value, x1, userData)
        
    Windows Only
    """
    if _os_name == 'nt':
        v = ctypes.c_double(Value)
        ud = ctypes.c_double(UserData)
        
        ec = staticLib.AddRequest(Handle, IOType, Channel, v, x1, ud)
        if ec != 0: raise LabJackException(ec)
    else:
       raise LabJackException(0, "Function only supported for Windows")


#Windows
def AddRequestS(Handle, pIOType, Channel, Value, x1, UserData):
    """Add a request to the LabJackUD request stack
    
    For Windows
    
    Sample Usage to get the AIN value from channel 0:
    
    >>> u3Handle = OpenLabJack(LJ_dtU3, LJ_ctUSB, "0", 1)
    >>> AddRequestS(u3Handle,"LJ_ioGET_AIN", 0, 0.0, 0, 0.0)
    >>> Go()
    >>> value = GetResult(u3Handle, LJ_ioGET_AIN, 0)
    >>> print("Value: " + str(value))
    Value: 0.366420765873
    
    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  IOType: String
    @param IOType: IO Request to the LabJack.
    @type  Channel: number
    @param Channel: Channel for the IO request.
    @type  Value: number
    @param Value: Used for some requests
    @type  x1: number
    @param x1: Used for some requests
    @type  UserData: number
    @param UserData: Used for some requests
    
    @rtype: None
    @return: Function returns nothing.
    
    @raise LabJackException:
    """
    if _os_name == 'nt':
        v = ctypes.c_double(Value)
        ud = ctypes.c_double(UserData)
        
        ec = staticLib.AddRequestS(Handle, pIOType, Channel, v, x1, ud)

        if ec != 0: raise LabJackException(ec)
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def AddRequestSS(Handle, pIOType, pChannel, Value, x1, UserData):
    """Add a request to the LabJackUD request stack
    
    For Windows
    
    Sample Usage to get the AIN value from channel 0:
    
    >>> u3Handle = OpenLabJack(LJ_dtU3, LJ_ctUSB, "0", 1)
    >>> AddRequestSS(u3Handle,"LJ_ioGET_CONFIG", "LJ_chFIRMWARE_VERSION", 0.0, 0, 0.0)
    >>> Go()
    >>> value = GetResultS(u3Handle, "LJ_ioGET_CONFIG", LJ_chFIRMWARE_VERSION)
    >>> print("Value: " + str(value))
    Value: 1.27
    
    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  IOType: String
    @param IOType: IO Request to the LabJack.
    @type  Channel: String
    @param Channel: Channel for the IO request.
    @type  Value: number
    @param Value: Used for some requests
    @type  x1: number
    @param x1: Used for some requests
    @type  UserData: number
    @param UserData: Used for some requests
    
    @rtype: None
    @return: Function returns nothing.
    
    @raise LabJackException:
    """
    if _os_name == 'nt':      
        v = ctypes.c_double(Value)
        ud = ctypes.c_double(UserData)
        
        ec = staticLib.AddRequestSS(Handle, pIOType, pChannel, v, x1, ud)

        if ec != 0: raise LabJackException(ec)
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def Go():
    """Complete all requests currently on the LabJackUD request stack

    For Windows Only
    
    Sample Usage:
    
    >>> u3Handle = OpenLabJack(LJ_dtU3, LJ_ctUSB, "0", 1)
    >>> AddRequestSS(u3Handle,"LJ_ioGET_CONFIG", "LJ_chFIRMWARE_VERSION", 0.0, 0, 0.0)
    >>> Go()
    >>> value = GetResultS(u3Handle, "LJ_ioGET_CONFIG", LJ_chFIRMWARE_VERSION)
    >>> print("Value: " + str(value))
    Value: 1.27
    
    @rtype: None
    @return: Function returns nothing.
    
    @raise LabJackException:
    """
    
    if _os_name == 'nt':
        ec = staticLib.Go()

        if ec != 0: raise LabJackException(ec)
    else:
       raise LabJackException("Function only supported for Windows")

#Windows
def GoOne(Handle):
    """Performs the next request on the LabJackUD request stack
    
    For Windows Only
    
    Sample Usage:
    
    >>> u3Handle = OpenLabJack(LJ_dtU3, LJ_ctUSB, "0", 1)
    >>> AddRequestSS(u3Handle,"LJ_ioGET_CONFIG", "LJ_chFIRMWARE_VERSION", 0.0, 0, 0.0)
    >>> GoOne(u3Handle)
    >>> value = GetResultS(u3Handle, "LJ_ioGET_CONFIG", LJ_chFIRMWARE_VERSION)
    >>> print("Value: " + str(value))
    Value: 1.27
    
    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    
    @rtype: None
    @return: Function returns nothing.
    
    @raise LabJackException:
    """
    if _os_name == 'nt':
        ec = staticLib.GoOne(Handle)

        if ec != 0: raise LabJackException(ec)
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def eGet(Handle, IOType, Channel, pValue, x1):
    """Perform one call to the LabJack Device
    
    eGet is equivilent to an AddRequest followed by a GoOne.
    
    For Windows Only
    
    Sample Usage:
    
    >>> eGet(u3Handle, LJ_ioGET_AIN, 0, 0, 0)
    0.39392614550888538
    
    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  IOType: number
    @param IOType: IO Request to the LabJack.
    @type  Channel: number
    @param Channel: Channel for the IO request.
    @type  Value: number
    @param Value: Used for some requests
    @type  x1: number
    @param x1: Used for some requests
    
    @rtype: number
    @return: Returns the value requested.
        - value
        
    @raise LabJackException:
    """
    if _os_name == 'nt':
        pv = ctypes.c_double(pValue)
        #ppv = ctypes.pointer(pv)
        ec = staticLib.eGet(Handle, IOType, Channel, ctypes.byref(pv), x1)
        #staticLib.eGet.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_long, ctypes.c_double, ctypes.c_long]
        #ec = staticLib.eGet(Handle, IOType, Channel, pValue, x1)
        
        if ec != 0: raise LabJackException(ec)
        #print("EGet:" + str(ppv))
        #print("Other:" + str(ppv.contents))
        return pv.value
    else:
       raise LabJackException(0, "Function only supported for Windows")


#Windows
#Raw method -- Used because x1 is an output
def eGetRaw(Handle, IOType, Channel, pValue, x1):
    """Perform one call to the LabJack Device as a raw command
    
    eGetRaw is equivilent to an AddRequest followed by a GoOne.
    
    For Windows Only
    
    Sample Usage (Calling a echo command):
    
    >>> sendBuff = [0] * 2
    >>> sendBuff[0] = 0x70
    >>> sendBuff[1] = 0x70
    >>> eGetRaw(ue9Handle, LJ_ioRAW_OUT, 0, len(sendBuff), sendBuff)
    (2.0, [112, 112])
    
    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  IOType: number
    @param IOType: IO Request to the LabJack.
    @type  Channel: number
    @param Channel: Channel for the IO request.
    @type  pValue: number
    @param Value: Length of the buffer.
    @type  x1: number
    @param x1: Buffer to send.
    
    @rtype: Tuple
    @return: The tuple (numBytes, returnBuffer)
        - numBytes (number)
        - returnBuffer (List)
        
    @raise LabJackException:
    """
    ec = 0
    x1Type = "int"
    if _os_name == 'nt':
        digitalConst = [35, 36, 37, 45]
        pv = ctypes.c_double(pValue)

        #If IOType is digital then call eget with x1 as a long
        if IOType in digitalConst:
            ec = staticLib.eGet(Handle, IOType, Channel, ctypes.byref(pv), x1)
        else: #Otherwise as an array
            
            try:
                #Verify x1 is an array
                if len(x1) < 1:
                    raise LabJackException(0, "x1 is not a valid variable for the given IOType") 
            except Exception:
                raise LabJackException(0, "x1 is not a valid variable for the given IOType")  
            
            #Initialize newA
            newA = None
            if type(x1[0]) == int:
                newA = (ctypes.c_byte*len(x1))()
                for i in range(len(x1)):
                    newA[i] = ctypes.c_byte(x1[i])
            else:
                x1Type = "float"
                newA = (ctypes.c_double*len(x1))()
                for i in range(len(x1)):
                    newA[i] = ctypes.c_double(x1[i])

            #Use eGetPtr when x1 is a pointer. x1 is a void*, and can accept 32
            #and 64-bit pointer addresses safely.
            if _use_ptr:
                ec = staticLib.eGetPtr(Handle, IOType, Channel, ctypes.byref(pv), ctypes.byref(newA))
            else:
                #Using eGet if eGetPtr is not available.
                ec = staticLib.eGet(Handle, IOType, Channel, ctypes.byref(pv), ctypes.byref(newA))
            
            if IOType == LJ_ioRAW_IN and Channel == 1:
                # We return the raw byte string if we are streaming
                x1 = pack('b' * len(x1), *newA)
            elif IOType == LJ_ioRAW_IN and Channel == 0:
                x1 = [0] * int(pv.value)
                for i in range(len(x1)):
                    x1[i] = newA[i] & 0xff
                
            else:
                x1 = [0] * len(x1)
                for i in range(len(x1)):
                    x1[i] = newA[i]
                    if x1Type == "int":
                        x1[i] = x1[i] & 0xff
            
        if ec != 0: raise LabJackException(ec)
        return pv.value, x1
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def eGetS(Handle, pIOType, Channel, pValue, x1):
    """Perform one call to the LabJack Device
    
    eGet is equivilent to an AddRequest followed by a GoOne.
    
    For Windows Only
    
    Sample Usage:
    
    >>> eGet(u3Handle, "LJ_ioGET_AIN", 0, 0, 0)
    0.39392614550888538
    
    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  pIOType: String
    @param pIOType: IO Request to the LabJack.
    @type  Channel: number
    @param Channel: Channel for the IO request.
    @type  Value: number
    @param Value: Used for some requests
    @type  x1: number
    @param x1: Used for some requests
    
    @rtype: number
    @return: Returns the value requested.
        - value
        
    @raise LabJackException:
    """
    if _os_name == 'nt':
        pv = ctypes.c_double(pValue)
        ec = staticLib.eGetS(Handle, pIOType, Channel, ctypes.byref(pv), x1)

        if ec != 0: raise LabJackException(ec)
        return pv.value
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def eGetSS(Handle, pIOType, pChannel, pValue, x1):
    """Perform one call to the LabJack Device
    
    eGet is equivilent to an AddRequest followed by a GoOne.
    
    For Windows Only
    
    Sample Usage:
    
    >>> eGetSS(u3Handle,"LJ_ioGET_CONFIG", "LJ_chFIRMWARE_VERSION", 0, 0)
    1.27
    
    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  pIOType: String
    @param pIOType: IO Request to the LabJack.
    @type  Channel: String
    @param Channel: Channel for the IO request.
    @type  Value: number
    @param Value: Used for some requests
    @type  x1: number
    @param x1: Used for some requests
    
    @rtype: number
    @return: Returns the value requested.
        - value
        
    @raise LabJackException:
    """
    if _os_name == 'nt':
        pv = ctypes.c_double(pValue)
        ec = staticLib.eGetSS(Handle, pIOType, pChannel, ctypes.byref(pv), x1)

        if ec != 0: raise LabJackException(ec)
        return pv.value
    else:
       raise LabJackException(0, "Function only supported for Windows")


#Windows
#Not currently implemented
def eGetRawS(Handle, pIOType, Channel, pValue, x1):
    """Function not yet implemented.
    
    For Windows only.
    """
    pass

#Windows
def ePut(Handle, IOType, Channel, Value, x1):
    """Put one value to the LabJack device
    
    ePut is equivilent to an AddRequest followed by a GoOne.
    
    For Windows Only
    
    Sample Usage:
    
    >>> u3Handle = OpenLabJack(LJ_dtU3, LJ_ctUSB, "0", 1)
    >>> eGet(u3Handle, LJ_ioGET_CONFIG, LJ_chLOCALID, 0, 0)
    0.0
    >>> ePut(u3Handle, LJ_ioPUT_CONFIG, LJ_chLOCALID, 8, 0)
    >>> eGet(u3Handle, LJ_ioGET_CONFIG, LJ_chLOCALID, 0, 0)
    8.0
    
    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  IOType: number
    @param IOType: IO Request to the LabJack.
    @type  Channel: number
    @param Channel: Channel for the IO request.
    @type  Value: number
    @param Value: Used for some requests
    @type  x1: number
    @param x1: Used for some requests
    
    @rtype: None
    @return: Function returns nothing.
    
    @raise LabJackException:
    """
    if _os_name == 'nt':
        pv = ctypes.c_double(Value)
        ec = staticLib.ePut(Handle, IOType, Channel, pv, x1)

        if ec != 0: raise LabJackException(ec)
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def ePutS(Handle, pIOType, Channel, Value, x1):
    """Put one value to the LabJack device
    
    ePut is equivilent to an AddRequest followed by a GoOne.
    
    For Windows Only
    
    Sample Usage:
    
    >>> u3Handle = OpenLabJack(LJ_dtU3, LJ_ctUSB, "0", 1)
    >>> eGet(u3Handle, LJ_ioGET_CONFIG, LJ_chLOCALID, 0, 0)
    0.0
    >>> ePutS(u3Handle, "LJ_ioPUT_CONFIG", LJ_chLOCALID, 8, 0)
    >>> eGet(u3Handle, LJ_ioGET_CONFIG, LJ_chLOCALID, 0, 0)
    8.0
    
    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  IOType: String
    @param IOType: IO Request to the LabJack.
    @type  Channel: number
    @param Channel: Channel for the IO request.
    @type  Value: number
    @param Value: Used for some requests
    @type  x1: number
    @param x1: Used for some requests
    
    @rtype: None
    @return: Function returns nothing.
    
    @raise LabJackException:
    """
    if _os_name == 'nt':
        pv = ctypes.c_double(Value)
        ec = staticLib.ePutS(Handle, pIOType, Channel, pv, x1)

        if ec != 0: raise LabJackException(ec)
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def ePutSS(Handle, pIOType, pChannel, Value, x1):
    """Put one value to the LabJack device
    
    ePut is equivilent to an AddRequest followed by a GoOne.
    
    For Windows Only
    
    Sample Usage:
    
    >>> u3Handle = OpenLabJack(LJ_dtU3, LJ_ctUSB, "0", 1)
    >>> eGet(u3Handle, LJ_ioGET_CONFIG, LJ_chLOCALID, 0, 0)
    0.0
    >>> ePutSS(u3Handle, "LJ_ioPUT_CONFIG", "LJ_chLOCALID", 8, 0)
    >>> eGet(u3Handle, LJ_ioGET_CONFIG, LJ_chLOCALID, 0, 0)
    8.0
    
    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  IOType: String
    @param IOType: IO Request to the LabJack.
    @type  Channel: String
    @param Channel: Channel for the IO request.
    @type  Value: number
    @param Value: Used for some requests
    @type  x1: number
    @param x1: Used for some requests
    
    @rtype: None
    @return: Function returns nothing.
    
    @raise LabJackException:
    """
    if _os_name == 'nt':
        pv = ctypes.c_double(Value)
        ec = staticLib.ePutSS(Handle, pIOType, pChannel, pv, x1)

        if ec != 0: raise LabJackException(ec)
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def GetResult(Handle, IOType, Channel):
    """Put one value to the LabJack device
    
    ePut is equivilent to an AddRequest followed by a GoOne.
    
    For Windows Only
    
    Sample Usage:
    
    >>> u3Handle = OpenLabJack(LJ_dtU3, LJ_ctUSB, "0", 1)
    >>> AddRequestSS(u3Handle,"LJ_ioGET_CONFIG", "LJ_chFIRMWARE_VERSION", 0.0, 0, 0.0)
    >>> GoOne(u3Handle)
    >>> value = GetResult(u3Handle, LJ_ioGET_CONFIG, LJ_chFIRMWARE_VERSION)
    >>> print("Value: " + str(value))
    Value: 1.27
    
    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  IOType: number
    @param IOType: IO Request to the LabJack.
    @type  Channel: number
    @param Channel: Channel for the IO request.
    
    @rtype: number
    @return: The value requested.
        - value
        
    @raise LabJackException:
    """
    if _os_name == 'nt':
        pv = ctypes.c_double()
        ec = staticLib.GetResult(Handle, IOType, Channel, ctypes.byref(pv))

        if ec != 0: raise LabJackException(ec)          
        return pv.value
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def GetResultS(Handle, pIOType, Channel):
    """Put one value to the LabJack device
    
    ePut is equivilent to an AddRequest followed by a GoOne.
    
    For Windows Only
    
    Sample Usage:
    
    >>> u3Handle = OpenLabJack(LJ_dtU3, LJ_ctUSB, "0", 1)
    >>> AddRequestSS(u3Handle,"LJ_ioGET_CONFIG", "LJ_chFIRMWARE_VERSION", 0.0, 0, 0.0)
    >>> GoOne(u3Handle)
    >>> value = GetResultS(u3Handle, "LJ_ioGET_CONFIG", LJ_chFIRMWARE_VERSION)
    >>> print("Value: " + str(value))
    Value: 1.27
    
    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  pIOType: String
    @param pIOType: IO Request to the LabJack.
    @type  Channel: number
    @param Channel: Channel for the IO request.
    
    @rtype: number
    @return: The value requested.
        - value
        
    @raise LabJackException:
    """
    if _os_name == 'nt':
        pv = ctypes.c_double()
        ec = staticLib.GetResultS(Handle, pIOType, Channel, ctypes.byref(pv))

        if ec != 0: raise LabJackException(ec)          
        return pv.value
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def GetResultSS(Handle, pIOType, pChannel):
    """Put one value to the LabJack device
    
    ePut is equivilent to an AddRequest followed by a GoOne.
    
    For Windows Only
    
    Sample Usage:
    
    >>> u3Handle = OpenLabJack(LJ_dtU3, LJ_ctUSB, "0", 1)
    >>> AddRequestSS(u3Handle,"LJ_ioGET_CONFIG", "LJ_chFIRMWARE_VERSION", 0.0, 0, 0.0)
    >>> GoOne(u3Handle)
    >>> value = GetResultSS(u3Handle, "LJ_ioGET_CONFIG", "LJ_chFIRMWARE_VERSION")
    >>> print("Value:" + str(value))
    Value: 1.27
    
    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  pIOType: String
    @param pIOType: IO Request to the LabJack.
    @type  Channel: String
    @param Channel: Channel for the IO request.
    
    @rtype: number
    @return: The value requested.
        - value
        
    @raise LabJackException:
    """
    if _os_name == 'nt':
        pv = ctypes.c_double()
        ec = staticLib.GetResultSS(Handle, pIOType, pChannel, ctypes.byref(pv))

        if ec != 0: raise LabJackException(ec)
        return pv.value
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def GetFirstResult(Handle):
    """List All LabJack devices of a specific type over a specific connection type.

    For Windows only.

    Sample Usage (Shows getting the localID (8) and firmware version (1.27) of a U3 device):

    >>> u3Handle = OpenLabJack(LJ_dtU3, LJ_ctUSB, "0", 1)
    >>> AddRequest(u3Handle, LJ_ioGET_CONFIG, LJ_chLOCALID, 0, 0, 0)
    >>> AddRequest(u3Handle, LJ_ioGET_CONFIG, LJ_chFIRMWARE_VERSION, 0, 0, 0)
    >>> Go()
    >>> GetFirstResult(u3Handle)
    (1001, 0, 8.0, 0, 0.0)
    >>> GetNextResult(u3Handle)
    (1001, 11, 1.27, 0, 0.0)

    @type  DeviceType: number
    @param DeviceType: The LabJack device.
    @type  ConnectionType: number
    @param ConnectionType: The connection method (Ethernet/USB).
    
    @rtype: Tuple
    @return: The tuple (ioType, channel, value, x1, userData)
        - ioType (number): The io of the result.
        - serialNumber (number): The channel of the result.
        - value (number): The requested result.
        - x1 (number):  Used only in certain requests.
        - userData (number): Used only in certain requests.
        
    @raise LabJackException: 
    """   
    if _os_name == 'nt':     
        pio = ctypes.c_long()
        pchan = ctypes.c_long()
        pv = ctypes.c_double()
        px = ctypes.c_long()
        pud = ctypes.c_double()
        ec = staticLib.GetFirstResult(Handle, ctypes.byref(pio), 
                                       ctypes.byref(pchan), ctypes.byref(pv), 
                                       ctypes.byref(px), ctypes.byref(pud))

        if ec != 0: raise LabJackException(ec)          
        return pio.value, pchan.value, pv.value, px.value, pud.value
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def GetNextResult(Handle):
    """List All LabJack devices of a specific type over a specific connection type.

    For Windows only.

    Sample Usage (Shows getting the localID (8) and firmware version (1.27) of a U3 device):

    >>> u3Handle = OpenLabJack(LJ_dtU3, LJ_ctUSB, "0", 1)
    >>> AddRequest(u3Handle, LJ_ioGET_CONFIG, LJ_chLOCALID, 0, 0, 0)
    >>> AddRequest(u3Handle, LJ_ioGET_CONFIG, LJ_chFIRMWARE_VERSION, 0, 0, 0)
    >>> Go()
    >>> GetFirstResult(u3Handle)
    (1001, 0, 8.0, 0, 0.0)
    >>> GetNextResult(u3Handle)
    (1001, 11, 1.27, 0, 0.0)

    @type  DeviceType: number
    @param DeviceType: The LabJack device.
    @type  ConnectionType: number
    @param ConnectionType: The connection method (Ethernet/USB).
    
    @rtype: Tuple
    @return: The tuple (ioType, channel, value, x1, userData)
        - ioType (number): The io of the result.
        - serialNumber (number): The channel of the result.
        - value (number): The requested result.
        - x1 (number):  Used only in certain requests.
        - userData (number): Used only in certain requests.
        
    @raise LabJackException: 
    """ 
    if _os_name == 'nt':
        pio = ctypes.c_long()
        pchan = ctypes.c_long()
        pv = ctypes.c_double()
        px = ctypes.c_long()
        pud = ctypes.c_double()
        ec = staticLib.GetNextResult(Handle, ctypes.byref(pio), 
                                       ctypes.byref(pchan), ctypes.byref(pv), 
                                       ctypes.byref(px), ctypes.byref(pud))

        if ec != 0: raise LabJackException(ec)          
        return pio.value, pchan.value, pv.value, px.value, pud.value
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def DoubleToStringAddress(number):
    """Converts a number (base 10) to an IP string.
    
    For Windows

    Sample Usage:

    >>> DoubleToStringAddress(3232235985)
    '192.168.1.209'
    
    @type  number: number
    @param number: Number to be converted.
    
    @rtype: String
    @return: The IP string converted from the number (base 10).
        
    @raise LabJackException: 
    """ 
    number = int(number)
    address = "%i.%i.%i.%i" % ((number >> 8*3 & 0xFF), (number >> 8*2 & 0xFF), (number >> 8 & 0xFF), (number & 0xFF))
    return address

def StringToDoubleAddress(pString):
    """Converts an IP string to a number (base 10).

    Sample Usage:

    >>> StringToDoubleAddress("192.168.1.209")
    3232235985L

    @type  pString: String
    @param pString: String to be converted.

    @rtype: number
    @return: The number (base 10) that represents the IP string.

    @raise LabJackException:
    """
    parts = pString.split('.')

    if len(parts) != 4:
        raise LabJackException(0, "IP address not correctly formatted")

    try:
        value = (int(parts[0]) << 8*3) + (int(parts[1]) << 8*2) + (int(parts[2]) << 8) + int(parts[3])
    except ValueError:
        raise LabJackException(0, "IP address not correctly formatted")

    return value

#Windows
def StringToConstant(pString):
    """Converts an LabJackUD valid string to its constant value.

    For Windows

    Sample Usage:

    >>> StringToConstant("LJ_dtU3")
    3
    
    @type  pString: String
    @param pString: String to be converted.
    
    @rtype: number
    @return: The number (base 10) that represents the LabJackUD string.
    """
    if _os_name == 'nt':
        a = ctypes.create_string_buffer(pString, 256)
        return staticLib.StringToConstant(a)
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def eAIN(Handle, ChannelP, ChannelN=199, Range=0, Resolution=0, Settling=0, Binary=False):
    """An easy function that returns a reading from one analog input.
        
    Windows Only

    Sample Usage:
    
    >>> import LabJackPython as LJUD
    >>> d = LJUD.openLabJack(LJUD.LJ_dtU3, LJUD.LJ_ctUSB, "0", 1)
    >>> AIN1Val = LJUD.eAIN(d.handle, 1)

    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  ChannelP: number
    @param ChannelP: The positive AIN channel to acquire.
    @type  ChannelN: number
    @param ChannelN: The negative AIN channel to acquire.
    @type  Range: number
    @param Range: Input range setting. Ignored on the U3.
    @type  Resolution: number
    @param Resolution: See Datasheet Section 2.6 and the eAIN function reference.
    @type  Settling: number
    @param Settling: See Datasheet Section 2.6 and the eAIN function reference.
    @type  Binary: boolean
    @param Binary: Setting to True or a non-zero value will return 
                   'Voltage' as a binary value.

    @rtype: number
    @return: Returns the analog input reading, which is generally a voltage.
    
    @raise LabJackException:
    """
    if _os_name == 'nt':
        chp = ctypes.c_long(ChannelP)
        chn = ctypes.c_long(ChannelN)
        volts = ctypes.c_double()
        rng = ctypes.c_long(Range)
        res = ctypes.c_long(Resolution)
        settling = ctypes.c_long(Settling)
        binary = ctypes.c_long(Binary)
        ec = staticLib.eAIN(Handle, chp, chn, ctypes.byref(volts), rng, res, settling, binary, 0, 0)
        if ec != 0: raise LabJackException(ec)
        return volts.value
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def eDAC(Handle, Channel, Voltage, Binary=False):
    """An easy function that writes a value to one analog output.
        
    Windows Only

    Sample Usage:
    
    >>> import LabJackPython as LJUD
    >>> d = LJUD.openLabJack(LJUD.LJ_dtU3, LJUD.LJ_ctUSB, "0", 1)
    >>> channel = 1 # target DAC1
    >>> voltage = 3.5   # Set the output to 3.5V
    >>> LJUD.eDAC(d.handle, channel, voltage)

    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  Channel: number
    @param Channel: DAC channel number.
    @type  Voltage: number
    @param Voltage: Desired voltage to output.
    @type  Binary: boolean
    @param Binary: Setting to True or a non-zero value will pass 
                   'Voltage' as a binary value.

    @rtype: None
    @return: Function returns nothing.
    
    @raise LabJackException:
    """
    if _os_name == 'nt':
        ch = ctypes.c_long(Channel)
        val = ctypes.c_double(Voltage)
        binary = ctypes.c_long(Binary)
        ec = staticLib.eDAC(Handle, ch, val, binary, 0, 0)
        if ec != 0: raise LabJackException(ec)
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def eDI(Handle, Channel):
    """An easy function that reads the state of one digital input.
        
    Windows Only

    Sample Usage:
    
    >>> import LabJackPython as LJUD
    >>> d = LJUD.openLabJack(LJUD.LJ_dtU3, LJUD.LJ_ctUSB, "0", 1)
    >>> FIO4State = LJUD.eDI(d.handle, 4)

    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  Channel: number
    @param Channel: DIO channel number.

    @rtype: number
    @return: Returns the state of the digital input. 0=False=Low, 1=True=High.
    
    @raise LabJackException:
    """
    if _os_name == 'nt':
        ch = ctypes.c_long(Channel)
        state = ctypes.c_long()
        ec = staticLib.eDI(Handle, ch, ctypes.byref(state))
        if ec != 0: raise LabJackException(ec)
        return state.value
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows
def eDO(Handle, Channel, State):
    """An easy function that writes the state of one digital output.
        
    Windows Only

    Sample Usage:
    
    >>> import LabJackPython as LJUD
    >>> d = LJUD.openLabJack(LJUD.LJ_dtU3, LJUD.LJ_ctUSB, "0", 1)
    >>> channel = 4 # target FIO4
    >>> state = 1   # Set the state to 1
    >>> LJUD.eDO(d.handle, channel, state)

    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  Channel: number
    @param Channel: DIO channel number.
    @type  State: number
    @param State: Desired state for the DIO.

    @rtype: None
    @return: Function returns nothing.
    
    @raise LabJackException:
    """
    if _os_name == 'nt':
        ch = ctypes.c_long(Channel)
        state = ctypes.c_long(State)
        ec = staticLib.eDO(Handle, ch, state)
        if ec != 0: raise LabJackException(ec)
    else:
       raise LabJackException(0, "Function only supported for Windows")

def _convertListToCtypeArray(li, cType):
    """Returns a ctypes list converted from a normal list."""
    return (cType*len(li))(*li)

#Windows
def eTCConfig(Handle, aEnableTimers, aEnableCounters, TCPinOffset, TimerClockBaseIndex, TimerClockDivisor, aTimerModes, aTimerValues):
    """An easy function that configures and initializes all the timers and counters.
        
    Windows Only

    Sample Usage:
    
    >>> import LabJackPython as LJUD
    >>> d = LJUD.openLabJack(LJUD.LJ_dtU3, LJUD.LJ_ctUSB, "0", 1)
    >>> aEnableTimers = [1,0] # Enable Timer0
    >>> aEnableCounters = [0,1] # Enable Counter1 (Counter0 unavailable when using clock with divisor)
    >>> pinOffset = 4 # Put Timer0 on FIO4 (Counter1 will be on FIO5)
    >>> clockBase = LJUD.LJ_tc48MHZ_DIV # 48MHz clock (allows divisor)
    >>> clockDivisor = 2 # clock will be 24MHz. This will allow a 24MHz/65535 = 366.217Hz PWM16
    >>> aTimerModes = [LJUD.LJ_tmPWM16, 0] # Set up PWM16
    >>> aTimerValues = [32768, 0] # Set 50% duty on the PWM16
    >>> LJUD.eTCConfig(d.handle, aEnableTimers, aEnableCounters, pinOffset, clockBase, clockDivisor, aTimerModes, aTimerValues)
    >>> aReadTimers = [0,0]
    >>> aUpdateResetTimers = [1,0] # Update Timer0
    >>> aReadCounters = [0,1] # Read Counter1
    >>> aResetCounters = [0,1] # Reset Counter1 after reading
    >>> aTimerValues = [16384,0] # Set PWM16 duty cycle to 75%
    >>> LJUD.eTCValues(d.handle, aReadTimers, aUpdateResetTimers, aReadCounters, aResetCounters, aTimerValues)

    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  aEnableTimers: list
    @param aEnableTimers: A list where each element specifies whether that timer is enabled.
                          A nonzero value for a list element specifies to enable that timer. 
                          List size must be equal to the number of timers available on the device.
    @type  aEnableCounters: list
    @param aEnableCounters: A list where each element specifies whether that counter is enabled.
                            A nonzero value for a list element specifies to enable that counter. 
                            List size must be equal to the number of counters available on the device.
    @type  TCPinOffset: number
    @param TCPinOffset: Value specifies where to start assigning timers and counters.
    @type  TimerClockBaseIndex: number
    @param TimerClockBaseIndex: Pass a constant to set the timer base clock. The default is device specific.
    @type  TimerClockDivisor: number
    @param TimerClockDivisor: Pass a divisor from 0-255 where 0 is a divisor of 256.
    @type  aTimerModes: list
    @param aTimerModes: A list where each element is a constant specifying the mode for that timer.
                        List size must be equal to the number of timers available on the device.
    @type  aTimerValues: list
    @param aTimerValues: A list where each element is specifies the initial value for that timer.
                         List size must be equal to the number of timers available on the device.

    @rtype: None
    @return: Function returns nothing.
    
    @raise LabJackException:
    """
    if _os_name == 'nt':
        numTimers = len(aEnableTimers)
        if numTimers != len(aTimerModes) or numTimers != len(aTimerValues):
            raise Exception("eTCConfig: Inconsistent timer list sizes. Timer list sizes must equal the number of timers on the device")
        for i in range(numTimers):
            if not isinstance(aEnableTimers[i], int):
                raise TypeError("aEnableTimers Expected an integer list but found an item " + str(type(aEnableTimers[i])) + ".")
            if not isinstance(aTimerModes[i], int):
                raise TypeError("aEnableTimers Expected an integer list but found an item " + str(type(aTimerModes[i])) + ".")
            if not isinstance(aTimerValues[i], int):
                raise TypeError("aEnableTimers Expected an integer list but found an item " + str(type(aTimerValues[i])) + ".")

        for x in aEnableCounters:
            if not isinstance(x, int):
                raise TypeError("aEnableCounters Expected an integer list but found an item " + str(type(x)) + ".")

        enTimers = _convertListToCtypeArray(aEnableTimers, ctypes.c_long)
        enCounters = _convertListToCtypeArray(aEnableCounters, ctypes.c_long)
        pinOffset = ctypes.c_long(TCPinOffset)
        clockBase = ctypes.c_long(TimerClockBaseIndex)
        clockDivisor = ctypes.c_long(TimerClockDivisor)
        tModes = _convertListToCtypeArray(aTimerModes, ctypes.c_long)
        tVals = _convertListToCtypeArray(aTimerValues, ctypes.c_double)
        ec = staticLib.eTCConfig(Handle, ctypes.byref(enTimers), ctypes.byref(enCounters), pinOffset, clockBase, clockDivisor, ctypes.byref(tModes), ctypes.byref(tVals), 0, 0)
        if ec != 0: raise LabJackException(ec)
    else:
       raise LabJackException(0, "Function only supported for Windows")

def _convertCtypeArrayToList(listCtype):
    """Returns a normal list from a ctypes list."""
    return listCtype[:]

#Windows
def eTCValues(Handle, aReadTimers, aUpdateResetTimers, aReadCounters, aResetCounters, aTimerValues):
    """An easy function that updates and reads all the timers and counters. 
        
    Windows Only

    For sample usage, see the eTCConfig definition.

    @type  Handle: number
    @param Handle: Handle to the LabJack device.
    @type  aReadTimers: list
    @param aReadTimers: A list where each element specifies whether to read that timer.
                        A nonzero value for a list element specifies to read that timer. 
    @type  aUpdateResetTimers: list
    @param aUpdateResetTimers: A list where each element specifies whether to update/reset that timer.
                               A nonzero value for a list element specifies to update/reset that timer.
    @type  aReadCounters: list
    @param aReadCounters: A list where each element specifies whether to read that counter.
                          A nonzero value for a list element specifies to read that counter. 
    @type  aResetCounters: list
    @param aResetCounters: A list where each element specifies whether to reset that counter.
                           A nonzero value for a list element specifies to reset that counter.
    @type  aTimerValues: list
    @param aTimerValues: A list where each element is specifies the initial value for that timer.
                         List size must be equal to the number of timers available on the device.

    @rtype: Tuple
    @return: The tuple (aTimerValues, aCounterValues)
        - aTimerValues: List where each element is the value read from that timer if the appropriate element is set in the aReadTimers array.
        - aCounterValues: List where each element is the value read from that counter if the appropriate element is set in the aReadCounters array.
    
    @raise LabJackException:
    """
    if _os_name == 'nt':
        numTimers = len(aReadTimers)
        numCounters = len(aReadCounters)

        if numTimers != len(aUpdateResetTimers) or numTimers != len(aTimerValues):
            raise Exception("eTCConfig: Inconsistent timer list sizes. Timer list sizes must equal the number of timers on the device")
        for i in range(numTimers):
            if not isinstance(aReadTimers[i], int):
                raise TypeError("aEnableTimers Expected an integer list but found an item " + str(type(aReadTimers[i])) + ".")
            if not isinstance(aUpdateResetTimers[i], int):
                raise TypeError("aEnableTimers Expected an integer list but found an item " + str(type(aUpdateResetTimers[i])) + ".")
            if not isinstance(aTimerValues[i], int):
                raise TypeError("aEnableTimers Expected an integer list but found an item " + str(type(aTimerValues[i])) + ".")

        if numCounters != len(aResetCounters):
            raise Exception("eTCConfig: Inconsistent counter list sizes. Counter list sizes must equal the number of Counters on the device")
        for i in range(numCounters):
            if not isinstance(aReadCounters[i], int):
                raise TypeError("aEnableCounters Expected an integer list but found an item " + str(type(aReadCounters[i])) + ".")
            if not isinstance(aResetCounters[i], int):
                raise TypeError("aEnableCounters Expected an integer list but found an item " + str(type(aResetCounters[i])) + ".")

        readTimers = _convertListToCtypeArray(aReadTimers, ctypes.c_long)
        updateTimers = _convertListToCtypeArray(aUpdateResetTimers, ctypes.c_long)
        readCounters = _convertListToCtypeArray(aReadCounters, ctypes.c_long)
        resetCounters = _convertListToCtypeArray(aResetCounters, ctypes.c_long)
        timerValues = _convertListToCtypeArray(aTimerValues, ctypes.c_double)
        aCounterValues = (ctypes.c_double*numCounters)()
        counterValues = _convertListToCtypeArray(aCounterValues, ctypes.c_double)
        ec = staticLib.eTCValues(Handle, ctypes.byref(readTimers), ctypes.byref(updateTimers), ctypes.byref(readCounters), ctypes.byref(resetCounters), ctypes.byref(timerValues), ctypes.byref(counterValues), 0, 0)
        if ec != 0: raise LabJackException(ec)
        tVals = _convertCtypeArrayToList(timerValues)
        cVals = _convertCtypeArrayToList(counterValues)
        return tVals, cVals
    else:
       raise LabJackException(0, "Function only supported for Windows")

# To hold all the error codes and what they mean:
ERROR_TO_STRING_DICT = dict()
ERROR_TO_STRING_DICT['1'] = ("SCRATCH_WRT_FAIL", "")
ERROR_TO_STRING_DICT['2'] = ("SCRATCH_ERASE_FAIL", "")
ERROR_TO_STRING_DICT['3'] = ("DATA_BUFFER_OVERFLOW", "")
ERROR_TO_STRING_DICT['4'] = ("ADC0_BUFFER_OVERFLOW", "")
ERROR_TO_STRING_DICT['5'] = ("FUNCTION_INVALID", "")
ERROR_TO_STRING_DICT['6'] = ("SWDT_TIME_INVALID", "This error is caused when an invalid time was passed to the watchdog.")
ERROR_TO_STRING_DICT['7'] = ("XBR_CONFIG_ERROR", "")
ERROR_TO_STRING_DICT['16'] = ("FLASH_WRITE_FAIL", "For some reason, the LabJack was unable to write the specified page of its internal flash.")
ERROR_TO_STRING_DICT['17'] = ("FLASH_ERASE_FAIL", "For some reason, the LabJack was unable to erase the specified page of its internal flash.")
ERROR_TO_STRING_DICT['18'] = ("FLASH_JMP_FAIL", "For some reason, the LabJack was unable to jump to a different section of flash. This may be an indication the flash is corrupted.")
ERROR_TO_STRING_DICT['19'] = ("FLASH_PSP_TIMEOUT", "")
ERROR_TO_STRING_DICT['20'] = ("FLASH_ABORT_RECEIVED", "")
ERROR_TO_STRING_DICT['21'] = ("FLASH_PAGE_MISMATCH", "")
ERROR_TO_STRING_DICT['22'] = ("FLASH_BLOCK_MISMATCH", "")
ERROR_TO_STRING_DICT['23'] = ("FLASH_PAGE_NOT_IN_CODE_AREA", "Usually, this error is raised when you try to write new firmware before upgrading the bootloader.")
ERROR_TO_STRING_DICT['24'] = ("MEM_ILLEGAL_ADDRESS", "")
ERROR_TO_STRING_DICT['25'] = ("FLASH_LOCKED", "Tried to write to flash before unlocking it.")
ERROR_TO_STRING_DICT['26'] = ("INVALID_BLOCK", "")
ERROR_TO_STRING_DICT['27'] = ("FLASH_ILLEGAL_PAGE", "")
ERROR_TO_STRING_DICT['28'] = ("FLASH_TOO_MANY_BYTES", "")
ERROR_TO_STRING_DICT['29'] = ("FLASH_INVALID_STRING_NUM", "")
ERROR_TO_STRING_DICT['40'] = ("SHT1x_COMM_TIME_OUT", "LabJack never received the ACK it was expecting from the SHT. This is usually due to incorrect wiring. Double check that all wires are securely connected to the correct pins.")
ERROR_TO_STRING_DICT['41'] = ("SHT1x_NO_ACK", "")
ERROR_TO_STRING_DICT['42'] = ("SHT1x_CRC_FAILED", "")
ERROR_TO_STRING_DICT['43'] = ("SHT1x_TOO_MANY_W_BYTES", "")
ERROR_TO_STRING_DICT['44'] = ("SHT1x_TOO_MANY_R_BYTES", "")
ERROR_TO_STRING_DICT['45'] = ("SHT1x_INVALID_MODE", "")
ERROR_TO_STRING_DICT['46'] = ("SHT1x_INVALID_LINE", "")
ERROR_TO_STRING_DICT['48'] = ("STREAM_IS_ACTIVE", "This error is raised when you call StreamStart after the stream has already been started.")
ERROR_TO_STRING_DICT['49'] = ("STREAM_TABLE_INVALID", "")
ERROR_TO_STRING_DICT['50'] = ("STREAM_CONFIG_INVALID", "")
ERROR_TO_STRING_DICT['52'] = ("STREAM_NOT_RUNNING", "This error is raised when you call StopStream after the stream has already been stopped.")
ERROR_TO_STRING_DICT['53'] = ("STREAM_INVALID_TRIGGER", "")
ERROR_TO_STRING_DICT['54'] = ("STREAM_ADC0_BUFFER_OVERFLOW", "")
ERROR_TO_STRING_DICT['55'] = ("STREAM_SCAN_OVERLAP", "This error is raised when a scan interrupt is fired before the LabJack has completed the previous scan. The most common cause of this error is a configuration with a high sampling rate and a large number of channels.")
ERROR_TO_STRING_DICT['56'] = ("STREAM_SAMPLE_NUM_INVALID", "")
ERROR_TO_STRING_DICT['57'] = ("STREAM_BIPOLAR_GAIN_INVALID", "")
ERROR_TO_STRING_DICT['58'] = ("STREAM_SCAN_RATE_INVALID", "")
ERROR_TO_STRING_DICT['59'] = ("STREAM_AUTORECOVER_ACTIVE", "This error is to inform you that the autorecover feature has been activated. Autorecovery is usually triggered by not reading data fast enough from the LabJack.")
ERROR_TO_STRING_DICT['60'] = ("STREAM_AUTORECOVER_REPORT", "This error marks the packet as an autorecovery report packet which contains how many packets were lost.")
ERROR_TO_STRING_DICT['63'] = ("STREAM_AUTORECOVER_OVERFLOW", "")
ERROR_TO_STRING_DICT['64'] = ("TIMER_INVALID_MODE", "")
ERROR_TO_STRING_DICT['65'] = ("TIMER_QUADRATURE_AB_ERROR", "")
ERROR_TO_STRING_DICT['66'] = ("TIMER_QUAD_PULSE_SEQUENCE", "")
ERROR_TO_STRING_DICT['67'] = ("TIMER_BAD_CLOCK_SOURCE", "")
ERROR_TO_STRING_DICT['68'] = ("TIMER_STREAM_ACTIVE", "")
ERROR_TO_STRING_DICT['69'] = ("TIMER_PWMSTOP_MODULE_ERROR", "")
ERROR_TO_STRING_DICT['70'] = ("TIMER_SEQUENCE_ERROR", "")
ERROR_TO_STRING_DICT['71'] = ("TIMER_LINE_SEQUENCE_ERROR", "")
ERROR_TO_STRING_DICT['72'] = ("TIMER_SHARING_ERROR", "")
ERROR_TO_STRING_DICT['80'] = ("EXT_OSC_NOT_STABLE", "")
ERROR_TO_STRING_DICT['81'] = ("INVALID_POWER_SETTING", "")
ERROR_TO_STRING_DICT['82'] = ("PLL_NOT_LOCKED", "")
ERROR_TO_STRING_DICT['96'] = ("INVALID_PIN", "")
ERROR_TO_STRING_DICT['97'] = ("PIN_CONFIGURED_FOR_ANALOG", "This error is raised when you try to do a digital operation on a pin that's configured for analog. Use a command like ConfigIO to set the pin to digital.")
ERROR_TO_STRING_DICT['98'] = ("PIN_CONFIGURED_FOR_DIGITAL", "This error is raised when you try to do an analog operation on a pin which is configured for digital. Use a command like ConfigIO to set the pin to analog.")
ERROR_TO_STRING_DICT['99'] = ("IOTYPE_SYNCH_ERROR", "")
ERROR_TO_STRING_DICT['100'] = ("INVALID_OFFSET", "")
ERROR_TO_STRING_DICT['101'] = ("IOTYPE_NOT_VALID", "")
ERROR_TO_STRING_DICT['102'] = ("TC_PIN_OFFSET_MUST_BE_4-8", "This error is raised when you try to configure the Timer/Counter pin offset to be 0-3.")
ERROR_TO_STRING_DICT['112'] = ("UART_TIMEOUT", "")
ERROR_TO_STRING_DICT['113'] = ("UART_NOT_CONNECTED", "")
ERROR_TO_STRING_DICT['114'] = ("UART_NOT_ENABLED", "")
ERROR_TO_STRING_DICT['115'] = ("UART_RXOVERFLOW", "")
ERROR_TO_STRING_DICT['116'] = ("I2C_BUS_BUSY", "")

def lowlevelErrorToString(errorcode):
    """Converts a low-level errorcode into a string.
    """
    try:
        name, advice = ERROR_TO_STRING_DICT[str(errorcode)]
    except KeyError:
        name = "UNKNOWN_ERROR"
        advice = "Unrecognized error code (%s)" % errorcode

    if advice != "":
        msg = "%s (%s)\n%s" % (name, errorcode, advice)
    else:
        msg = "%s (%s)" % (name, errorcode)

    return msg

#Windows
def ErrorToString(ErrorCode):
    """Converts an LabJackUD valid error code to a String.

    For Windows

    Sample Usage:

    >>> ErrorToString(1007)
    'LabJack not found'
    
    @type  ErrorCode: number
    @param ErrorCode: Valid LabJackUD error code.
    
    @rtype: String
    @return: The string that represents the valid LabJackUD error code
    """
    if _os_name == 'nt':
        pString = ctypes.create_string_buffer(256)
        staticLib.ErrorToString(ctypes.c_long(ErrorCode), ctypes.byref(pString))
        return pString.value
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows, Linux, and Mac
def GetDriverVersion():
    """Gets the version of the UD driver on Windows or the Exodriver on
    Linux/Mac.

    For Windows, Linux, and Mac

    Sample Usage:

    >>> GetDriverVersion()
    2.6400

    @rtype: String
    @return: Driver version number as a String.
    """
    if _os_name == 'nt':
        staticLib.GetDriverVersion.restype = ctypes.c_double
        return "%.4f" % staticLib.GetDriverVersion()
        
    elif _os_name == 'posix':
        staticLib.LJUSB_GetLibraryVersion.restype = ctypes.c_float
        return "%.4f" % staticLib.LJUSB_GetLibraryVersion()

#Windows
def TCVoltsToTemp(TCType, TCVolts, CJTempK):
    """Converts a thermo couple voltage reading to an appropriate temperature reading.

    For Windows

    Sample Usage:

    >>> TCVoltsToTemp(LJ_ttK, 0.003141592, 297.038889)
    373.13353222244825
            
    @type  TCType: number
    @param TCType: The type of thermo couple used.
    @type  TCVolts: number
    @param TCVolts: The voltage reading from the thermo couple
    @type  CJTempK: number
    @param CJTempK: The cold junction temperature reading in Kelvin
    
    @rtype: number
    @return: The thermo couples temperature reading
        - pTCTempK
        
    @raise LabJackException:
    """
    if _os_name == 'nt':
        pTCTempK = ctypes.c_double()
        ec = staticLib.TCVoltsToTemp(ctypes.c_long(TCType), ctypes.c_double(TCVolts), 
                                     ctypes.c_double(CJTempK), ctypes.byref(pTCTempK))

        if ec != 0: raise LabJackException(ec)          
        return pTCTempK.value
    else:
       raise LabJackException(0, "Function only supported for Windows")


#Windows 
def Close():
    """Resets the driver and closes all open handles.

    For Windows

    Sample Usage:

    >>> Close()
            
    @rtype: None
    @return: The function returns nothing.
    """    
    if _os_name == 'nt':
        staticLib.Close()
    else:
       raise LabJackException(0, "Function only supported for Windows")

#Windows, Linux and Mac
def DriverPresent():
    try:
        #Windows
        ctypes.windll.LoadLibrary("labjackud")
        return True
    except:
        try:
            #Cygwin/Windows
            ctypes.cdll.LoadLibrary("labjackud")
            return True
        except:
            try:
                #Linux
                ctypes.cdll.LoadLibrary("liblabjackusb.so")
                return True
            except:
                try:
                    #Mac
                    ctypes.cdll.LoadLibrary("liblabjackusb.dylib")
                    return True
                except:
                    return False
    return False
        
#Currently Windows only
def U12DriverPresent():
    try:
        ctypes.windll.LoadLibrary("ljackuw")
        return True
    except:
        try:
            ctypes.cdll.LoadLibrary("ljackuw")
            return True
        except:
            return False
    return False


#Windows only
def LJHash(hashStr, size):
    """An approximation of the md5 hashing algorithms.  

    For Windows
    
    An approximation of the md5 hashing algorithm.  Used 
    for authorizations on UE9 version 1.73 and higher and u3 
    version 1.35 and higher.

    @type  hashStr: String
    @param hashStr: String to be hashed.
    @type  size: number
    @param size: Amount of bytes to hash from the hashStr
            
    @rtype: String
    @return: The hashed string.
    """  
    
    outBuff = (ctypes.c_char * 16)()
    retBuff = ''
    
    ec = staticLib.LJHash(ctypes.cast(hashStr, ctypes.POINTER(ctypes.c_char)),
                          size, 
                          ctypes.cast(outBuff, ctypes.POINTER(ctypes.c_char)), 
                          0)
    if ec != 0: raise LabJackException(ec)

    for i in range(16):
        retBuff += outBuff[i]
        
    return retBuff

def __listAllUE9Unix(connectionType):
    """Private listAll function for use on unix and mac machines to find UE9s.
    """

    deviceList = {}
    rcvDataBuff = []

    if connectionType == LJ_ctUSB:
        numDevices = staticLib.LJUSB_GetDevCount(LJ_dtUE9)
    
        for i in range(numDevices):
            try:
                device = openLabJack(LJ_dtUE9, 1, firstFound = False, devNumber = i+1)
                device.close()
            
                deviceList[str(device.serialNumber)] = device.__dict__
            except LabJackException:
                pass

    elif connectionType == LJ_ctETHERNET:
        #Create a socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(BROADCAST_SOCKET_TIMEOUT)

        sndDataBuff = [0] * 6
        sndDataBuff[0] = 0x22
        sndDataBuff[1] = 0x78
        sndDataBuff[3] = 0xa9

        outBuff = ""
        for item in sndDataBuff:
            outBuff += chr(item)
        s.sendto(outBuff, ("255.255.255.255", 52362))

        try:
            while True:
                rcvDataBuff = s.recv(128)
                try:
                    rcvDataBuff = [ord(val) for val in rcvDataBuff]
                    if verifyChecksum(rcvDataBuff):
                        #Parse the packet
                        macAddress = rcvDataBuff[28:34]
                        macAddress.reverse()

                        # The serial number is four bytes:
                        # 0x10 and the last three bytes of the MAC address
                        serialBytes = chr(0x10)
                        for j in macAddress[3:]:
                            serialBytes += chr(j)
                        serial = unpack(">I", serialBytes)[0]

                        #Parse out the IP address
                        ipAddress = ""
                        for j in range(13, 9, -1):
                            ipAddress += str(int(rcvDataBuff[j]))
                            ipAddress += "." 
                        ipAddress = ipAddress[0:-1]

                        #Local ID
                        localId = rcvDataBuff[8] & 0xff

                        deviceList[serial] = dict(devType = LJ_dtUE9, localId = localId, \
                                                    serialNumber = serial, ipAddress = ipAddress)
                except Exception:
                    pass
        except:
            pass

    return deviceList



def __listAllU3Unix():
    """Private listAll function for unix and mac machines.  Works on the U3 only.
    """
    deviceList = {}
    numDevices = staticLib.LJUSB_GetDevCount(LJ_dtU3)

    for i in range(numDevices):
        try:
            device = openLabJack(LJ_dtU3, 1, firstFound = False, devNumber = i+1)
            device.close()
            
            deviceList[str(device.serialNumber)] = device.__dict__
        except LabJackException:
            pass
        

    return deviceList


def __listAllU6Unix():
    """ List all for U6s """
    deviceList = {}
    numDevices = staticLib.LJUSB_GetDevCount(LJ_dtU6)

    for i in range(numDevices):
        try:
            device = openLabJack(LJ_dtU6, 1, firstFound = False, devNumber = i+1)
            device.close()
        
            deviceList[str(device.serialNumber)] = device.__dict__
        except LabJackException:
            pass

    return deviceList

def setChecksum16(buffer):
    total = 0;

    for i in range(6, len(buffer)):
        total += (buffer[i] & 0xff)

    buffer[4] = (total & 0xff)
    buffer[5] = ((total >> 8) & 0xff)

    return buffer


def setChecksum8(buffer, numBytes):
    total = 0

    for i in range(1, numBytes):
        total += (buffer[i] & 0xff)

    buffer[0] = (total & 0xff) + ((total >> 8) & 0xff)
    buffer[0] = (buffer[0] & 0xff) + ((buffer[0] >> 8) & 0xff)

    return buffer


class LJSocketHandle(object):
    """
    Class to replace a device handle with a socket to a LJSocket server.
    """
    def __init__(self, ipAddress, port, devType, firstFound, pAddress):
        try:
            serverSocket = socket.socket()
            serverSocket.connect((ipAddress, port))
            serverSocket.settimeout(SOCKET_TIMEOUT)
            
            f = serverSocket.makefile(bufsize = 0)
            f.write("scan\r\n")
            
            l = f.readline().strip()
            try:
                status, numLines = l.split(' ')
            except ValueError:
                raise Exception("Got invalid line from server: %s" % l)
                
            if status.lower().startswith('ok'):
                lines = []
                marked = None
                for i in range(int(numLines)):
                    l = f.readline().strip()
                    dev = parseline(l)
                    
                    if devType == dev['prodId']:
                        lines.append(dev)
                        
                        if not firstFound and (dev['localId'] == pAddress or dev['serial'] == pAddress):
                            marked = dev                 
                
                f.close()
                serverSocket.close()
                
                #print("Result of scan:")
                #print(lines)
                
                if firstFound and len(lines) > 0:
                    marked = lines[0]
                elif marked is not None:
                    pass
                else:
                    raise Exception("LabJack not found.")
                    
                if marked['crPort'] != 'x':
                    self.crSocket = socket.socket()
                    self.crSocket.connect((ipAddress, marked['crPort']))
                    self.crSocket.settimeout(LJSOCKET_TIMEOUT)
                else:
                    self.crSocket = None
                    
                if marked['modbusPort'] != 'x':
                    self.modbusSocket = socket.socket()
                    self.modbusSocket.connect((ipAddress, marked['modbusPort']))
                    self.modbusSocket.settimeout(LJSOCKET_TIMEOUT)
                else:
                    self.modbusSocket = None
                    
                if marked['spontPort'] != 'x':
                    self.spontSocket = socket.socket()
                    self.spontSocket.connect((ipAddress, marked['spontPort']))
                    self.spontSocket.settimeout(LJSOCKET_TIMEOUT)
                else:
                    self.spontSocket = None
                
            else:
                raise Exception("Got an error from LJSocket. It said '%s'" % l)
            
        except Exception:
            e = sys.exc_info()[1]
            raise LabJackException(ec = LJE_LABJACK_NOT_FOUND, errorString = "Couldn't connect to a LabJack at %s:%s. The error was: %s" % (ipAddress, port, str(e)))
    
    def close(self):
        if self.crSocket is not None:
            self.crSocket.close()
            
        if self.modbusSocket is not None:
            self.modbusSocket.close()
            
        if self.spontSocket is not None:
            self.spontSocket.close()

        
def parseline(line):
    prodId, crPort, modbusPort, spontPort, localId, serial = line.split(' ')
    if not crPort.startswith('x'):
        crPort = int(crPort)
    if not modbusPort.startswith('x'):
        modbusPort = int(modbusPort)
    if not spontPort.startswith('x'):
        spontPort = int(spontPort)
    
    return { 'prodId' : int(prodId), 'crPort' : crPort, 'modbusPort' : modbusPort, 'spontPort' : spontPort, 'localId' : int(localId), 'serial' : int(serial)  }


#Class for handling UE9 TCP Connections
class UE9TCPHandle(object):
    """__UE9TCPHandle(ipAddress)

    Creates two sockets for the streaming and non streaming ports on the UE9.
    Also, tries to create a socket for the Modbus port.  Only works on
    default ports (Data 52360, Stream 52361, Modbus 502).
    """

    def __init__(self, ipAddress, timeout = SOCKET_TIMEOUT):
        try:
            self.data = socket.socket()
            self.data.settimeout(timeout)
            self.data.connect((ipAddress, 52360))
            
            self.stream = socket.socket()
            self.stream.settimeout(timeout)
            self.stream.connect((ipAddress, 52361))
            
            try:
                self.modbus = socket.socket()
                self.modbus.settimeout(timeout)
                self.modbus.connect((ipAddress, 502))
            except socket.error:
                e = sys.exc_info()[1]
                self.modbus = None
        except Exception:
            e = sys.exc_info()[1]
            print(e)
            raise LabJackException("Couldn't open sockets to the UE9 at IP Address %s. Error was: %s" % (ipAddress, e))

    def close(self):
        try:
            self.data.close()
            self.stream.close()
            self.modbus.close()
        except Exception:
            e = sys.exc_info()[1]
            print("UE9 Handle close exception: %s" % e)
            pass

def toDouble(bytes):
    """
    Name: toDouble(buffer)
    Args: buffer, an array with 8 bytes
    Desc: Converts the 8 byte array into a floating point number.
    """
    right, left = unpack("<Ii", pack("B" * 8, *bytes[0:8]))

    return float(left) + float(right)/(2**32)

def hexWithoutQuotes(l):
    """
    Return a string listing hex without all the single quotes.

    >>> l = range(10)
    >>> print(hexWithoutQuotes(l))
    [0x0, 0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7, 0x8, 0x9]

    """
    return str([hex(i) for i in l]).replace("'", "")

def toList(buffer):
    """
    Takes a list, bytes object or string and converts it to a list
    of integers.

    Args:
        buffer: A list, bytes object or string.

    Returns:
        A list of integers.
    """
    if isinstance(buffer, str):
        return [ord(ch) for ch in buffer]
    else:
        return [int(val) for val in buffer]

def streamByteToInt(byte):
    """
    Takes a byte from a stream read packet, which could be a
    string or integer from the bytes object, and and converts it
    to an integer.

    Args:
        x: A byte (chr or int) from a stream read.

    Returns:
        The converted integer.
    """
    if _use_py2:
        return ord(byte)
    else:
        return byte


# device types:
LJ_dtUE9 = 9
LJ_dtU3 = 3
LJ_dtU6 = 6

# connection types:
LJ_ctUSB = 1 # UE9 + U3 + U6
LJ_ctETHERNET = 2 # UE9 only


# Raw connection types are used to open a device but not communicate with it
# should only be used if the normal connection types fail and for testing.
# If a device is opened with the raw connection types, only LJ_ioRAW_OUT
# and LJ_ioRAW_IN io types should be used
LJ_ctUSB_RAW = 101 # UE9 + U3 + U6
LJ_ctETHERNET_RAW = 102 # UE9 only


LJ_ctLJSOCKET = 200 # Connection type for USB LabJack connected to LJSocket server

# io types:
LJ_ioGET_AIN = 10 # UE9 + U3 + U6.  This is single ended version.
LJ_ioGET_AIN_DIFF = 15  # U3 + U6.  Put second channel in x1.  For U3, if 32 is
                        # passed as x1, Vref will be added to the result.

LJ_ioPUT_AIN_RANGE = 2000 # UE9 + U6
LJ_ioGET_AIN_RANGE = 2001 # UE9 + U6

# sets or reads the analog or digital mode of the FIO and EIO pins.  FIO is Channel 0-7, EIO 8-15
LJ_ioPUT_ANALOG_ENABLE_BIT = 2013 # U3
LJ_ioGET_ANALOG_ENABLE_BIT = 2014 # U3

# sets or reads the analog or digital mode of the FIO and EIO pins. Channel is starting 
# bit #, x1 is number of bits to read. The pins are set by passing a bitmask as a double
# for the value.  The first bit of the int that the double represents will be the setting 
# for the pin number sent into the channel variable. 
LJ_ioPUT_ANALOG_ENABLE_PORT = 2015 # U3
LJ_ioGET_ANALOG_ENABLE_PORT = 2016 # U3

LJ_ioPUT_DAC = 20 # UE9 + U3 + U6
LJ_ioPUT_DAC_ENABLE = 2002 # UE9 + U3 (U3 on Channel 1 only)
LJ_ioGET_DAC_ENABLE = 2003 # UE9 + U3 (U3 on Channel 1 only)

LJ_ioGET_DIGITAL_BIT = 30 # UE9 + U3 + U6.  Changes direction of bit to input as well.
LJ_ioGET_DIGITAL_BIT_DIR = 31 # U3 + U6
LJ_ioGET_DIGITAL_BIT_STATE = 32 # does not change direction of bit, allowing readback of output

# channel is starting bit #, x1 is number of bits to read 
LJ_ioGET_DIGITAL_PORT = 35 # UE9 + U3 + U6.  Changes direction of bits to input as well.
LJ_ioGET_DIGITAL_PORT_DIR = 36 # U3 + U6
LJ_ioGET_DIGITAL_PORT_STATE = 37 # does not change direction of bits, allowing readback of output

# digital put commands will set the specified digital line(s) to output
LJ_ioPUT_DIGITAL_BIT = 40 # UE9 + U3
# channel is starting bit #, value is output value, x1 is bits to write
LJ_ioPUT_DIGITAL_PORT = 45 # UE9 + U3

# Used to create a pause between two events in a U3 and U6 low-level feedback
# command.  For example, to create a 100 ms positive pulse on FIO0, add a
# request to set FIO0 high, add a request for a wait of 100000, add a
# request to set FIO0 low, then Go.  Channel is ignored.  Value is
# microseconds to wait and should range from 0 to 8388480.  The actual
# resolution of the wait is 128 microseconds on a U3 and 64 microseconds
# on a U6.
LJ_ioPUT_WAIT = 70 # U3 + U6

# counter.  Input only.
LJ_ioGET_COUNTER = 50 # UE9 + U3 + U6

LJ_ioPUT_COUNTER_ENABLE = 2008 # UE9 + U3 + U6
LJ_ioGET_COUNTER_ENABLE = 2009 # UE9 + U3 + U6

# This will cause the designated counter to reset.    If you want to reset the
# counter with every read, you have to use this command every time.
LJ_ioPUT_COUNTER_RESET = 2012  # UE9 + U3 + U6

# on UE9: timer only used for input. Output Timers don't use these.  Only Channel used.
# on U3: Channel used (0 or 1).
# on U6: Channel used (0 to 3).
LJ_ioGET_TIMER = 60 # UE9 + U3 + U6

LJ_ioPUT_TIMER_VALUE = 2006 # UE9 + U3 + U6.  Value gets new value
LJ_ioPUT_TIMER_MODE = 2004 # UE9 + U3 + U6.  On both Value gets new mode.
LJ_ioGET_TIMER_MODE = 2005 # UE9

# IOTypes for use with SHT sensor.  For LJ_ioSHT_GET_READING, a channel of LJ_chSHT_TEMP (5000) will
# read temperature, and LJ_chSHT_RH (5001) will read humidity.
LJ_ioSHT_GET_READING = 500 # UE9 + U3 + U6.

# Uses settings from LJ_chSPI special channels (set with LJ_ioPUT_CONFIG) to communcaite with
# something using an SPI interface.  The value parameter is the number of bytes to transfer
# and x1 is the address of the buffer.  The data from the buffer will be sent, then overwritten
# with the data read.  The channel parameter is ignored.
LJ_ioSPI_COMMUNICATION = 503 # UE9 + U3 + U6

LJ_ioI2C_COMMUNICATION = 504 # UE9 + U3 + U6
LJ_ioASYNCH_COMMUNICATION = 505 # UE9 + U3 + U6
LJ_ioTDAC_COMMUNICATION = 506 # UE9 + U3 + U6

# Set's the U3 to it's original configuration.    This means sending the following
# to the ConfigIO and TimerClockConfig low level functions
#
# ConfigIO
# Byte #
# 6       WriteMask       15      Write all parameters.
# 8       TimerCounterConfig      0          No timers/counters.  Offset=0.
# 9       DAC1Enable      0          DAC1 disabled.
# 10      FIOAnalog       0          FIO all digital.
# 11      EIOAnalog       0          EIO all digital.
# 
# 
# TimerClockConfig
# Byte #
# 8          TimerClockConfig          130      Set clock to 24 MHz.
# 9          TimerClockDivisor          0          Divisor = 0.
LJ_ioPIN_CONFIGURATION_RESET = 2017 # U3

# the raw in/out are unusual, channel # corresponds to the particular comm port, which
# depends on the device.  For example, on the UE9, 0 is main comm port, and 1 is the streaming comm.
# Make sure and pass a porter to a char buffer in x1, and the number of bytes desired in value.  A call
# to GetResult will return the number of bytes actually read/written.  The max you can send out in one call
# is 512 bytes to the UE9 and 16384 bytes to the U3.
LJ_ioRAW_OUT = 100 # UE9 + U3 + U6
LJ_ioRAW_IN = 101 # UE9 + U3 + U6

LJ_ioRAWMB_OUT = 104 # Used with LJ_ctETHERNET_MB to send raw modbus commands to the modbus TCP/IP Socket
LJ_ioRAWMB_IN = 105

# sets the default power up settings based on the current settings of the device AS THIS DLL KNOWS.  This last part
# basically means that you should set all parameters directly through this driver before calling this.  This writes 
# to flash which has a limited lifetime, so do not do this too often.  Rated endurance is 20,000 writes.
LJ_ioSET_DEFAULTS = 103 # U3

# Requests to create the list of channels to stream.  Usually you will use the CLEAR_STREAM_CHANNELS request first, which
# will clear any existing channels, then use ADD_STREAM_CHANNEL multiple times to add your desired channels.  Note that
# you can do CLEAR, and then all your ADDs in a single Go() as long as you add the requests in order.
LJ_ioADD_STREAM_CHANNEL = 200 # UE9 + U3 + U6
# Put negative channel in x1.  If 32 is passed as x1, Vref will be added to the result.
LJ_ioADD_STREAM_CHANNEL_DIFF = 206 # U3 + U6

LJ_ioCLEAR_STREAM_CHANNELS = 201
LJ_ioSTART_STREAM = 202
LJ_ioSTOP_STREAM = 203

LJ_ioADD_STREAM_DAC = 207

# Get stream data has several options.  If you just want to get a single channel's data (if streaming multiple channels), you
# can pass in the desired channel #, then the number of data points desired in Value, and a pointer to an array to put the
# data into as X1.  This array needs to be an array of doubles. Therefore, the array needs to be 8 * number of
# requested data points in byte length. What is returned depends on the StreamWaitMode.  If None, this function will only return
# data available at the time of the call.  You therefore must call GetResult() for this function to retrieve the actually number
# of points retreived.  If Pump or Sleep, it will return only when the appropriate number of points have been read or no
# new points arrive within 100ms.  Since there is this timeout, you still need to use GetResult() to determine if the timeout
# occured.  If AllOrNone, you again need to check GetResult.

# You can also retreive the entire scan by passing LJ_chALL_CHANNELS.  In this case, the Value determines the number of SCANS 
# returned, and therefore, the array must be 8 * number of scans requested * number of channels in each scan.  Likewise
# GetResult() will return the number of scans, not the number of data points returned.

# Note: data is stored interleaved across all streaming channels.  In other words, if you are streaming two channels, 0 and 1, 
# and you request LJ_chALL_CHANNELS, you will get, Channel0, Channel1, Channel0, Channel1, etc.     Once you have requested the 
# data, any data returned is removed from the internal buffer, and the next request will give new data.

# Note: if reading the data channel by channel and not using LJ_chALL_CHANNELS, the data is not removed from the internal buffer
# until the data from the last channel in the scan is requested.  This means that if you are streaming three channels, 0, 1 and 2,
# and you request data from channel 0, then channel 1, then channel 0 again, the request for channel 0 the second time will
# return the exact same amount of data.     Also note, that the amount of data that will be returned for each channel request will be
# the same until you've read the last channel in the scan, at which point your next block may be a different size.

# Note: although more convenient, requesting individual channels is slightly slower then using LJ_chALL_CHANNELS.  Since you
# are probably going to have to split the data out anyway, we have saved you the trouble with this option.

# Note: if you are only scanning one channel, the Channel parameter is ignored.

LJ_ioGET_STREAM_DATA = 204

# U3 only:

# Channel = 0 buzz for a count, Channel = 1 buzz continuous
# Value is the Period
# X1 is the toggle count when channel = 0
LJ_ioBUZZER = 300 # U3 

# config iotypes:
LJ_ioPUT_CONFIG = 1000 # UE9 + U3 + U6
LJ_ioGET_CONFIG = 1001 # UE9 + U3 + U6

# channel numbers used for CONFIG types:
# UE9 + U3 + U6
LJ_chLOCALID = 0 # UE9 + U3 + U6
LJ_chHARDWARE_VERSION = 10 # UE9 + U3 + U6 (Read Only)
LJ_chSERIAL_NUMBER = 12 # UE9 + U3 + U6 (Read Only)
LJ_chFIRMWARE_VERSION = 11 # UE9 + U3 + U6 (Read Only)
LJ_chBOOTLOADER_VERSION = 15 # UE9 + U3 + U6 (Read Only)
LJ_chPRODUCTID = 8 # UE9 + U3 + U6 (Read Only)

# UE9 specific:
LJ_chCOMM_POWER_LEVEL = 1 # UE9
LJ_chIP_ADDRESS = 2 # UE9
LJ_chGATEWAY = 3 # UE9
LJ_chSUBNET = 4 # UE9
LJ_chPORTA = 5 # UE9
LJ_chPORTB = 6 # UE9
LJ_chDHCP = 7 # UE9
LJ_chPRODUCTID = 8 # UE9
LJ_chMACADDRESS = 9 # UE9
LJ_chCOMM_FIRMWARE_VERSION = 11 # UE9
LJ_chCONTROL_POWER_LEVEL = 13 # UE9 
LJ_chCONTROL_FIRMWARE_VERSION = 14 # UE9 (Read Only)
LJ_chCONTROL_BOOTLOADER_VERSION = 15 # UE9 (Read Only)
LJ_chCONTROL_RESET_SOURCE = 16 # UE9 (Read Only)
LJ_chUE9_PRO = 19 # UE9 (Read Only)

# U3 only:
# sets the state of the LED
LJ_chLED_STATE = 17 # U3  value = LED state

LJ_chSDA_SCL = 18 # U3  enable / disable SDA/SCL as digital I/O

LJ_chU3HV = 22 # U3 (Read Only) Value will be 1 for a U3-HV and 0 for a U3-LV
               # or a U3 with hardware version < 1.30

# U6 only:
LJ_chU6_PRO = 23

# Driver related:
# Number of milliseconds that the driver will wait for communication to complete
LJ_chCOMMUNICATION_TIMEOUT = 20
LJ_chSTREAM_COMMUNICATION_TIMEOUT = 21

# Used to access calibration and user data.  The address of an array is passed in as x1.
# For the UE9, a 1024-element buffer of bytes is passed for user data and a 128-element
# buffer of doubles is passed for cal constants.
# For the U3, a 256-element buffer of bytes is passed for user data and a 12-element
# buffer of doubles is passed for cal constants.
# The layout of cal ants are defined in the users guide for each device.
# When the LJ_chCAL_CONSTANTS special channel is used with PUT_CONFIG, a
# special value (0x4C6C) must be passed in to the Value parameter. This makes it
# more difficult to accidently erase the cal constants.  In all other cases the Value
# parameter is ignored.
LJ_chCAL_CONSTANTS = 400 # UE9 + U3 + U6
LJ_chUSER_MEM = 402 # UE9 + U3 + U6

# Used to write and read the USB descriptor strings.  This is generally for OEMs
# who wish to change the strings.
# Pass the address of an array in x1.  Value parameter is ignored.
# The array should be 128 elements of bytes.  The first 64 bytes are for the
# iManufacturer string, and the 2nd 64 bytes are for the iProduct string.
# The first byte of each 64 byte block (bytes 0 and 64) contains the number
# of bytes in the string.  The second byte (bytes 1 and 65) is the USB spec
# value for a string descriptor (0x03).     Bytes 2-63 and 66-127 contain unicode
# encoded strings (up to 31 characters each).
LJ_chUSB_STRINGS = 404 # U3


# timer/counter related
LJ_chNUMBER_TIMERS_ENABLED = 1000 # UE9 + U3 + U6
LJ_chTIMER_CLOCK_BASE = 1001 # UE9 + U3 + U6
LJ_chTIMER_CLOCK_DIVISOR = 1002 # UE9 + U3 + U6
LJ_chTIMER_COUNTER_PIN_OFFSET = 1003 # U3 + U6

# AIn related
LJ_chAIN_RESOLUTION = 2000 # UE9 + U3 + U6
LJ_chAIN_SETTLING_TIME = 2001 # UE9 + U3 + U6
LJ_chAIN_BINARY = 2002 # UE9 + U3 + U6

# DAC related
LJ_chDAC_BINARY = 3000 # UE9 + U3 + U6

# SHT related
LJ_chSHT_TEMP = 5000 # UE9 + U3 + U6
LJ_chSHT_RH = 5001 # UE9 + U3 + U6
LJ_chSHT_DATA_CHANNEL = 5002 # UE9 + U3 + U6. Default is FIO0
LJ_chSHT_CLOCK_CHANNEL = 5003 # UE9 + U3 + U6. Default is FIO1

# SPI related
LJ_chSPI_AUTO_CS = 5100 # UE9 + U3 + U6
LJ_chSPI_DISABLE_DIR_CONFIG = 5101 # UE9 + U3 + U6
LJ_chSPI_MODE = 5102 # UE9 + U3 + U6
LJ_chSPI_CLOCK_FACTOR = 5103 # UE9 + U3 + U6
LJ_chSPI_MOSI_PINNUM = 5104 # UE9 + U3 + U6
LJ_chSPI_MISO_PINNUM = 5105 # UE9 + U3 + U6
LJ_chSPI_CLK_PINNUM = 5106 # UE9 + U3 + U6
LJ_chSPI_CS_PINNUM = 5107 # UE9 + U3 + U6

# I2C related :
# used with LJ_ioPUT_CONFIG
LJ_chI2C_ADDRESS_BYTE = 5108 # UE9 + U3 + U6
LJ_chI2C_SCL_PIN_NUM = 5109 # UE9 + U3 + U6
LJ_chI2C_SDA_PIN_NUM = 5110 # UE9 + U3 + U6
LJ_chI2C_OPTIONS = 5111 # UE9 + U3 + U6
LJ_chI2C_SPEED_ADJUST = 5112 # UE9 + U3 + U6

# used with LJ_ioI2C_COMMUNICATION :
LJ_chI2C_READ = 5113 # UE9 + U3 + U6
LJ_chI2C_WRITE = 5114 # UE9 + U3 + U6
LJ_chI2C_GET_ACKS = 5115 # UE9 + U3 + U6
LJ_chI2C_WRITE_READ = 5130 # UE9 + U3

# ASYNCH related :
# Used with LJ_ioASYNCH_COMMUNICATION
LJ_chASYNCH_RX = 5117 # UE9 + U3 + U6
LJ_chASYNCH_TX = 5118 # UE9 + U3 + U6
LJ_chASYNCH_FLUSH = 5128 # UE9 + U3 + U6
LJ_chASYNCH_ENABLE = 5129 # UE9 + U3 + U6

# Used with LJ_ioPUT_CONFIG and LJ_ioGET_CONFIG
LJ_chASYNCH_BAUDFACTOR = 5127 # UE9 + U3 + U6

# LJ TickDAC related :
LJ_chTDAC_SCL_PIN_NUM = 5119 # UE9 + U3 + U6:  Used with LJ_ioPUT_CONFIG
# Used with LJ_ioTDAC_COMMUNICATION
LJ_chTDAC_SERIAL_NUMBER = 5120 # UE9 + U3 + U6: Read only
LJ_chTDAC_READ_USER_MEM = 5121 # UE9 + U3 + U6
LJ_chTDAC_WRITE_USER_MEM = 5122 # UE9 + U3 + U6
LJ_chTDAC_READ_CAL_CONSTANTS = 5123 # UE9 + U3 + U6
LJ_chTDAC_WRITE_CAL_CONSTANTS = 5124 # UE9 + U3 + U6
LJ_chTDAC_UPDATE_DACA = 5125 # UE9 + U3 + U6
LJ_chTDAC_UPDATE_DACB = 5126 # UE9 + U3 + U6

# stream related.  Note, Putting to any of these values will stop any running streams.
LJ_chSTREAM_SCAN_FREQUENCY = 4000
LJ_chSTREAM_BUFFER_SIZE = 4001
LJ_chSTREAM_CLOCK_OUTPUT = 4002
LJ_chSTREAM_EXTERNAL_TRIGGER = 4003
LJ_chSTREAM_WAIT_MODE = 4004
LJ_chSTREAM_DISABLE_AUTORECOVERY = 4005 # U3 + U6
LJ_chSTREAM_SAMPLES_PER_PACKET = 4108
LJ_chSTREAM_READS_PER_SECOND = 4109
LJ_chAIN_STREAM_SETTLING_TIME = 4110 # U6

# readonly stream related
LJ_chSTREAM_BACKLOG_COMM = 4105
LJ_chSTREAM_BACKLOG_CONTROL = 4106
LJ_chSTREAM_BACKLOG_UD = 4107

# special channel #'s
LJ_chALL_CHANNELS = -1
LJ_INVALID_CONSTANT = -999


# Thermocouple Type constants.
LJ_ttB = 6001
LJ_ttE = 6002
LJ_ttJ = 6003
LJ_ttK = 6004
LJ_ttN = 6005
LJ_ttR = 6006
LJ_ttS = 6007
LJ_ttT = 6008


# other constants:
# ranges (not all are supported by all devices):
LJ_rgBIP20V = 1   # -20V to +20V
LJ_rgBIP10V = 2   # -10V to +10V
LJ_rgBIP5V = 3    # -5V to +5V
LJ_rgBIP4V = 4    # -4V to +4V
LJ_rgBIP2P5V = 5  # -2.5V to +2.5V
LJ_rgBIP2V = 6    # -2V to +2V
LJ_rgBIP1P25V = 7 # -1.25V to +1.25V
LJ_rgBIP1V = 8    # -1V to +1V
LJ_rgBIPP625V = 9 # -0.625V to +0.625V
LJ_rgBIPP1V = 10  # -0.1V to +0.1V
LJ_rgBIPP01V = 11 # -0.01V to +0.01V

LJ_rgUNI20V = 101    # 0V to +20V
LJ_rgUNI10V = 102    # 0V to +10V
LJ_rgUNI5V = 103     # 0V to +5V
LJ_rgUNI4V = 104     # 0V to +4V
LJ_rgUNI2P5V = 105   # 0V to +2.5V
LJ_rgUNI2V = 106     # 0V to +2V
LJ_rgUNI1P25V = 107  # 0V to +1.25V
LJ_rgUNI1V = 108     # 0V to +1V
LJ_rgUNIP625V = 109  # 0V to +0.625V
LJ_rgUNIP25V = 112   # 0V to +0.25V
LJ_rgUNIP500V = 110  # 0V to +0.500V
LJ_rgUNIP3125V = 111 # 0V to +0.3125V
LJ_rgUNIP025V = 113  # 0V to +0.025V
LJ_rgUNIP0025V = 114 # 0V to +0.0025V

# timer modes:
LJ_tmPWM16 = 0 # 16 bit PWM
LJ_tmPWM8 = 1 # 8 bit PWM
LJ_tmRISINGEDGES32 = 2 # 32-bit rising to rising edge measurement
LJ_tmFALLINGEDGES32 = 3 # 32-bit falling to falling edge measurement
LJ_tmDUTYCYCLE = 4 # duty cycle measurement
LJ_tmFIRMCOUNTER = 5 # firmware based rising edge counter
LJ_tmFIRMCOUNTERDEBOUNCE = 6 # firmware counter with debounce
LJ_tmFREQOUT = 7 # frequency output
LJ_tmQUAD = 8 # Quadrature
LJ_tmTIMERSTOP = 9 # stops another timer after n pulses
LJ_tmSYSTIMERLOW = 10 # read lower 32-bits of system timer
LJ_tmSYSTIMERHIGH = 11 # read upper 32-bits of system timer
LJ_tmRISINGEDGES16 = 12 # 16-bit rising to rising edge measurement
LJ_tmFALLINGEDGES16 = 13 # 16-bit falling to falling edge measurement

# timer clocks:
LJ_tc750KHZ = 0 # UE9: 750 khz 
LJ_tcSYS = 1    # UE9: system clock

LJ_tc2MHZ = 10       # U3: Hardware Version 1.20 or lower
LJ_tc6MHZ = 11       # U3: Hardware Version 1.20 or lower
LJ_tc24MHZ = 12      # U3: Hardware Version 1.20 or lower
LJ_tc500KHZ_DIV = 13 # U3: Hardware Version 1.20 or lower
LJ_tc2MHZ_DIV = 14   # U3: Hardware Version 1.20 or lower
LJ_tc6MHZ_DIV = 15   # U3: Hardware Version 1.20 or lower
LJ_tc24MHZ_DIV = 16  # U3: Hardware Version 1.20 or lower

LJ_tc4MHZ = 20        # U3: Hardware Version 1.21 or higher
LJ_tc12MHZ = 21       # U3: Hardware Version 1.21 or higher
LJ_tc48MHZ = 22       # U3: Hardware Version 1.21 or higher
LJ_tc1000KHZ_DIV = 23 # U3: Hardware Version 1.21 or higher
LJ_tc4MHZ_DIV = 24    # U3: Hardware Version 1.21 or higher
LJ_tc12MHZ_DIV = 25   # U3: Hardware Version 1.21 or higher
LJ_tc48MHZ_DIV = 26   # U3: Hardware Version 1.21 or higher

# stream wait modes
LJ_swNONE = 1  # no wait, return whatever is available
LJ_swALL_OR_NONE = 2 # no wait, but if all points requested aren't available, return none.
LJ_swPUMP = 11 # wait and pump the message pump.  Prefered when called from primary thread (if you don't know
               # if you are in the primary thread of your app then you probably are.  Do not use in worker
               # secondary threads (i.e. ones without a message pump).
LJ_swSLEEP = 12 # wait by sleeping (don't do this in the primary thread of your app, or it will temporarily 
                # hang)    This is usually used in worker secondary threads.


# BETA CONSTANTS
# Please note that specific usage of these constants and their values might change

# SWDT
# Sets parameters used to control the software watchdog option.  The device is only
# communicated with and updated when LJ_ioSWDT_CONFIG is used with LJ_chSWDT_ENABLE
# or LJ_chSWDT_DISABLE.  Thus, to change a value, you must use LJ_io_PUT_CONFIG
# with the appropriate channel constant so set the value inside the driver, then call
# LJ_ioSWDT_CONFIG to enable that change.
LJ_ioSWDT_CONFIG = 507 # UE9 + U3 + U6 - Use with LJ_chSWDT_ENABLE or LJ_chSWDT_DISABLE
LJ_ioSWDT_STROKE = 508 # UE9 - Used when SWDT_STRICT_ENABLE is turned on to renew the watchdog.

LJ_chSWDT_ENABLE = 5200 # UE9 + U3 + U6 - used with LJ_ioSWDT_CONFIG to enable watchdog.  Value paramter is number of seconds to trigger
LJ_chSWDT_DISABLE = 5201 # UE9 + U3 + U6 - used with LJ_ioSWDT_CONFIG to disable watchdog.

# Used with LJ_io_PUT_CONFIG
LJ_chSWDT_RESET_DEVICE= 5202 # U3 + U6 - Reset U3 or U6 on watchdog reset.  Write only.
LJ_chSWDT_RESET_COMM = 5203 # UE9 - Reset Comm on watchdog reset.  Write only.
LJ_chSWDT_RESET_CONTROL = 5204 # UE9 - Reset Control on watchdog trigger.  Write only.
LJ_chSWDT_UDPATE_DIOA = 5205 # UE9 + U3 + U6 - Update DIO0 settings after reset.  Write only.
LJ_chSWDT_UPDATE_DIOB = 5206 # UE9 - Update DIO1 settings after reset.  Write only.
LJ_chSWDT_DIOA_CHANNEL = 5207 # UE9 + U3 + U6 - DIO0 channel to be set after reset.  Write only.
LJ_chSWDT_DIOA_STATE = 5208 # UE9 + U3 + U6 - DIO0 state to be set after reset.  Write only.
LJ_chSWDT_DIOB_CHANNEL = 5209 # UE9 - DIO1 channel to be set after reset.  Write only.
LJ_chSWDT_DIOB_STATE = 5210 # UE9 - DIO0 state to be set after reset.  Write only.
LJ_chSWDT_UPDATE_DAC0 = 5211 # UE9 - Update DAC0 settings after reset.  Write only.
LJ_chSWDT_UPDATE_DAC1 = 5212 # UE9 - Update DAC1 settings after reset.  Write only.
LJ_chSWDT_DAC0 = 5213 # UE9 - voltage to set DAC0 at on watchdog reset.  Write only.
LJ_chSWDT_DAC1 = 5214 # UE9 - voltage to set DAC1 at on watchdog reset.  Write only.
LJ_chSWDT_DAC_ENABLE = 5215 # UE9 - Enable DACs on watchdog reset.  Default is true.  Both DACs are enabled or disabled togeather.  Write only.
LJ_chSWDT_STRICT_ENABLE = 5216 # UE9 - Watchdog will only renew with LJ_ioSWDT_STROKE command.
LJ_chSWDT_INITIAL_ROLL_TIME = 5217 # UE9 - Watchdog timer for the first cycle when powered on, after watchdog triggers a reset the normal value is used.  Set to 0 to disable.

# END BETA CONSTANTS


# error codes:    These will always be in the range of -1000 to 3999 for labView compatibility (+6000)
LJE_NOERROR = 0

LJE_INVALID_CHANNEL_NUMBER = 2 # occurs when a channel that doesn't exist is specified (i.e. DAC #2 on a UE9), or data from streaming is requested on a channel that isn't streaming
LJE_INVALID_RAW_INOUT_PARAMETER = 3
LJE_UNABLE_TO_START_STREAM = 4
LJE_UNABLE_TO_STOP_STREAM = 5
LJE_NOTHING_TO_STREAM = 6
LJE_UNABLE_TO_CONFIG_STREAM = 7
LJE_BUFFER_OVERRUN = 8 # occurs when stream buffer overruns (this is the driver buffer not the hardware buffer).  Stream is stopped.
LJE_STREAM_NOT_RUNNING = 9
LJE_INVALID_PARAMETER = 10
LJE_INVALID_STREAM_FREQUENCY = 11
LJE_INVALID_AIN_RANGE = 12
LJE_STREAM_CHECKSUM_ERROR = 13 # occurs when a stream packet fails checksum.  Stream is stopped
LJE_STREAM_COMMAND_ERROR = 14 # occurs when a stream packet has invalid command values.     Stream is stopped.
LJE_STREAM_ORDER_ERROR = 15 # occurs when a stream packet is received out of order (typically one is missing).    Stream is stopped.
LJE_AD_PIN_CONFIGURATION_ERROR = 16 # occurs when an analog or digital request was made on a pin that isn't configured for that type of request
LJE_REQUEST_NOT_PROCESSED = 17 # When a LJE_AD_PIN_CONFIGURATION_ERROR occurs, all other IO requests after the request that caused the error won't be processed. Those requests will return this error.


# U3 Specific Errors
LJE_SCRATCH_ERROR = 19
LJE_DATA_BUFFER_OVERFLOW = 20
LJE_ADC0_BUFFER_OVERFLOW = 21 
LJE_FUNCTION_INVALID = 22
LJE_SWDT_TIME_INVALID = 23
LJE_FLASH_ERROR = 24
LJE_STREAM_IS_ACTIVE = 25
LJE_STREAM_TABLE_INVALID = 26
LJE_STREAM_CONFIG_INVALID = 27
LJE_STREAM_BAD_TRIGGER_SOURCE = 28
LJE_STREAM_INVALID_TRIGGER = 30
LJE_STREAM_ADC0_BUFFER_OVERFLOW = 31
LJE_STREAM_SAMPLE_NUM_INVALID = 33
LJE_STREAM_BIPOLAR_GAIN_INVALID = 34
LJE_STREAM_SCAN_RATE_INVALID = 35
LJE_TIMER_INVALID_MODE = 36
LJE_TIMER_QUADRATURE_AB_ERROR = 37
LJE_TIMER_QUAD_PULSE_SEQUENCE = 38
LJE_TIMER_BAD_CLOCK_SOURCE = 39
LJE_TIMER_STREAM_ACTIVE = 40
LJE_TIMER_PWMSTOP_MODULE_ERROR = 41
LJE_TIMER_SEQUENCE_ERROR = 42
LJE_TIMER_SHARING_ERROR = 43
LJE_TIMER_LINE_SEQUENCE_ERROR = 44
LJE_EXT_OSC_NOT_STABLE = 45
LJE_INVALID_POWER_SETTING = 46
LJE_PLL_NOT_LOCKED = 47
LJE_INVALID_PIN = 48
LJE_IOTYPE_SYNCH_ERROR = 49
LJE_INVALID_OFFSET = 50
LJE_FEEDBACK_IOTYPE_NOT_VALID = 51
LJE_CANT_CONFIGURE_PIN_FOR_ANALOG = 67
LJE_CANT_CONFIGURE_PIN_FOR_DIGITAL = 68
LJE_TC_PIN_OFFSET_MUST_BE_4_TO_8 = 70
LJE_INVALID_DIFFERENTIAL_CHANNEL = 71
LJE_DSP_SIGNAL_OUT_OF_RANGE = 72

# other errors
LJE_SHT_CRC = 52
LJE_SHT_MEASREADY = 53
LJE_SHT_ACK = 54
LJE_SHT_SERIAL_RESET = 55
LJE_SHT_COMMUNICATION = 56

LJE_AIN_WHILE_STREAMING = 57

LJE_STREAM_TIMEOUT = 58
LJE_STREAM_CONTROL_BUFFER_OVERFLOW = 59
LJE_STREAM_SCAN_OVERLAP = 60
LJE_FIRMWARE_VERSION_IOTYPE = 61
LJE_FIRMWARE_VERSION_CHANNEL = 62
LJE_FIRMWARE_VERSION_VALUE = 63
LJE_HARDWARE_VERSION_IOTYPE = 64
LJE_HARDWARE_VERSION_CHANNEL = 65
LJE_HARDWARE_VERSION_VALUE = 66

LJE_LJTDAC_ACK_ERROR = 69


LJE_MIN_GROUP_ERROR = 1000 # all errors above this number will stop all requests, below this number are request level errors.

LJE_UNKNOWN_ERROR = 1001 # occurs when an unknown error occurs that is caught, but still unknown.
LJE_INVALID_DEVICE_TYPE = 1002 # occurs when devicetype is not a valid device type
LJE_INVALID_HANDLE = 1003 # occurs when invalid handle used
LJE_DEVICE_NOT_OPEN = 1004    # occurs when Open() fails and AppendRead called despite.
LJE_NO_DATA_AVAILABLE = 1005 # this is cause when GetData() called without calling DoRead(), or when GetData() passed channel that wasn't read
LJE_NO_MORE_DATA_AVAILABLE = 1006
LJE_LABJACK_NOT_FOUND = 1007 # occurs when the labjack is not found at the given id or address.
LJE_COMM_FAILURE = 1008 # occurs when unable to send or receive the correct # of bytes
LJE_CHECKSUM_ERROR = 1009
LJE_DEVICE_ALREADY_OPEN = 1010 # occurs when LabJack is already open via USB in another program or process
LJE_COMM_TIMEOUT = 1011
LJE_USB_DRIVER_NOT_FOUND = 1012
LJE_INVALID_CONNECTION_TYPE = 1013
LJE_INVALID_MODE = 1014
LJE_DEVICE_NOT_CONNECTED = 1015 # occurs when a LabJack that was opened is no longer connected to the system

# These errors aren't actually generated by the UD, but could be handy in your code to indicate an event as an error code without
# conflicting with LabJack error codes
LJE_DISCONNECT = 2000
LJE_RECONNECT = 2001

# and an area for your own codes.  This area won't ever be used for LabJack codes.
LJE_MIN_USER_ERROR = 3000
LJE_MAX_USER_ERROR = 3999

# warning are negative
LJE_DEVICE_NOT_CALIBRATED = -1 # defaults used instead
LJE_UNABLE_TO_READ_CALDATA = -2 # defaults used instead


# deprecated constants:
LJ_ioANALOG_INPUT = 10
LJ_ioANALOG_OUTPUT = 20 # UE9 + U3
LJ_ioDIGITAL_BIT_IN = 30 # UE9 + U3
LJ_ioDIGITAL_PORT_IN = 35 # UE9 + U3 
LJ_ioDIGITAL_BIT_OUT = 40 # UE9 + U3
LJ_ioDIGITAL_PORT_OUT = 45 # UE9 + U3
LJ_ioCOUNTER = 50 # UE9 + U3
LJ_ioTIMER = 60 # UE9 + U3
LJ_ioPUT_COUNTER_MODE = 2010 # UE9
LJ_ioGET_COUNTER_MODE = 2011 # UE9
LJ_ioGET_TIMER_VALUE = 2007 # UE9
LJ_ioCYCLE_PORT = 102  # UE9 
LJ_chTIMER_CLOCK_CONFIG = 1001 # UE9 + U3 
LJ_ioPUT_CAL_CONSTANTS = 400
LJ_ioGET_CAL_CONSTANTS = 401
LJ_ioPUT_USER_MEM = 402
LJ_ioGET_USER_MEM = 403
LJ_ioPUT_USB_STRINGS = 404
LJ_ioGET_USB_STRINGS = 405
LJ_ioSHT_DATA_CHANNEL = 501 # UE9 + U3
LJ_ioSHT_CLOCK_CHANNEL = 502 # UE9 + U3
LJ_chI2C_ADDRESS = 5108 # UE9 + U3
LJ_chASYNCH_CONFIG = 5116 # UE9 + U3
LJ_rgUNIP500V = 110 # 0V to +0.500V
LJ_ioENABLE_POS_PULLDOWN = 2018 # U6
LJ_ioENABLE_NEG_PULLDOWN = 2019 # U6
LJ_rgAUTO = 0
