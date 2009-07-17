"""
" A UE9 class to rock your face off. Inspired by u3.py
"
"""
from LabJackPython import *

import struct, socket, select

def parseIpAddress(bytes):
    return "%s.%s.%s.%s" % (bytes[3], bytes[2], bytes[1], bytes[0] )
    
def unpackInt(bytes):
    return struct.unpack("<I", struct.pack("BBBB", *bytes))[0]

def unpackShort(bytes):
    return struct.unpack("<H", struct.pack("BB", *bytes))[0]

class UE9(Device):
    """ A nice python class to represent a UE9 """
    def __init__(self):
        """
        Name: UE9.__init__(self)
        Args: None
        Desc: Your basic constructor.
        
        >>> myUe9 = ue9.UE9()
        """
        self.devType = 9
        self.ipAdress = None
        self.localId = None
        self.handle = None
        self.debug = False
    
    def open(self, firstFound = True, ipAddress = None, localId = None, devNumber = None, ethernet=False):
        """
        Name: UE9.open(firstFound = True, ipAddress = None, localId = None, devNumber = None, ethernet=False)
        Args: firstFound, Open the first found UE9
              ipAddress, Specify the IP Address of the UE9 you want to open
              localId, Specify the localId of the UE9 you want to open
              devNumber, Specify the USB dev number of the UE9
              ethernet, set to true to connect over ethernet.
        Desc: Opens the UE9.
        
        >>> myUe9 = ue9.UE9()
        >>> myUe9.open()
        """
        Device.open(self, 9, Ethernet = ethernet, firstFound = firstFound, localId = localId, devNumber = devNumber, ipAddress = ipAddress)
        
    def commConfig(self, LocalID = None, IPAddress = None, Gateway = None, Subnet = None, PortA = None, PortB = None, DHCPEnabled = None):
        """
        Name: UE9.commConfig(LocalID = None, IPAddress = None, Gateway = None,
                Subnet = None, PortA = None, PortB = None, DHCPEnabled = None)
        Args: LocalID, Set the LocalID
              IPAddress, Set the IPAdress 
              Gateway, Set the Gateway
              Subnet, Set the Subnet
              PortA, Set Port A
              PortB, Set Port B
              DHCPEnabled, True = Enabled, False = Disabled
        Desc: Writes and reads various configuration settings associated
              with the Comm processor. Section 5.2.1 of the User's Guide.
        
        >>> myUe9 = ue9.UE9()
        >>> myUe9.open()
        >>> myUe9.commConfig()
        {'CommFWVersion': '1.47',
         'DHCPEnabled': False,
         'Gateway': '192.168.1.1',
         'HWVersion': '1.10',
         'IPAddress': '192.168.1.114',
         'LocalID': 1,
         'MACAddress': 'XX:XX:XX:XX:XX:XX',
         'PortA': 52360,
         'PortB': 52361,
         'PowerLevel': 0,
         'ProductID': 9,
         'SerialNumber': 27121XXXX,
         'Subnet': '255.255.255.0'}
        """
        command = [ 0 ] * 38
        
        #command[0] = Checksum8
        command[1] = 0x78
        command[2] = 0x10
        command[3] = 0x01
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        #command[6] = Writemask. Set it along the way.
        #command[7] = Reserved
        if LocalID != None:
            command[6] |= 1
            command[8] = LocalID
        
        if IPAddress != None:
            command[6] |= (1 << 2)
            ipbytes = IPAddress.split('.')
            ipbytes = [ int(x) for x in ipbytes ]
            ipbytes.reverse()
            command[10:14] = ipbytes
        
        if Gateway != None:
            command[6] |= (1 << 3)
            gwbytes = Gateway.split('.')
            gwbytes = [ int(x) for x in gwbytes ]
            gwbytes.reverse()
            command[14:18] = gwbytes
            
        if Subnet != None:
            command[6] |= (1 << 4)
            snbytes = Subnet.split('.')
            snbytes = [ int(x) for x in snbytes ]
            snbytes.reverse()
            command[18:21] = gwbytes
            
        if PortA != None:
            command[6] |= (1 << 5)
            t = struct.pack("<H", PortA)
            command[22] = ord(t[0])
            command[23] = ord(t[1])
        
        if PortB != None:
            command[6] |= (1 << 5)
            t = struct.pack("<H", PortB)
            command[22] = ord(t[0])
            command[23] = ord(t[1])

        if DHCPEnabled != None:
            command[6] |= (1 << 6)
            if DHCPEnabled:
                command[26] = 1
        
        result = self._writeRead(command, 38, [ 0x78, 0x10, 0x01 ])
        self.localId = result[8]
        self.powerLevel = result[9]
        self.ipAddress = parseIpAddress(result[10:14])
        self.gateway = parseIpAddress(result[14:18])
        self.subnet = parseIpAddress(result[18:22])
        self.portA = struct.unpack("<H", struct.pack("BB", *result[22:24]))[0]
        self.portB = struct.unpack("<H", struct.pack("BB", *result[24:26]))[0]
        self.DHCPEnabled = bool(result[26])
        self.productId = result[27]
        macBytes = result[28:34]
        self.macAddress = "%02X:%02X:%02X:%02X:%02X:%02X" % (result[33], result[32], result[31], result[30], result[29], result[28])
        
        self.serialNumber = struct.unpack("<I", struct.pack("BBBB", result[28], result[29], result[30], 0x10))[0]
        
        self.hwVersion = "%s.%s" % (result[35], result[34])
        self.commFWVersion = "%s.%s" % (result[37], result[36])
        
        return { 'LocalID' : self.localId, 'PowerLevel' : self.powerLevel, 'IPAddress' : self.ipAddress, 'Gateway' : self.gateway, 'Subnet' : self.subnet, 'PortA' : self.portA, 'PortB' : self.portB, 'DHCPEnabled' : self.DHCPEnabled, 'ProductID' : self.productId, 'MACAddress' : self.macAddress, 'HWVersion' : self.hwVersion, 'CommFWVersion' : self.commFWVersion, 'SerialNumber' : self.serialNumber}
    
    def flushBuffer(self):
        """
        Name: UE9.flushBuffer()
        Args: None
        Desc: Resets the pointers to the stream buffer to make it empty.
        
        >>> myUe9 = ue9.UE9()
        >>> myUe9.open()
        >>> myUe9.flushBuffer()
        """
        command = [ 0x08, 0x08 ]
        self._writeRead(command, 2, [], False)
    
    def discoveryUDP(self):
        """
        Name: UE9.discoveryUDP()
        Args: None
        Desc: Sends a UDP Broadcast packet and returns a dictionary of the
              result. The dictionary contains all the things that are in the
              commConfig dictionary.
        
        >>> myUe9 = ue9.UE9()
        >>> myUe9.discoveryUDP()
        {'192.168.1.114': {'CommFWVersion': '1.47', ... },
         '192.168.1.209': {'CommFWVersion': '1.47', ... }}
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        host = '255.255.255.255'
        port = 52362
        addr = (host,port)
        
        sndBuffer = [0] * 6
        sndBuffer[0] = 0x22
        sndBuffer[1] = 0x78
        sndBuffer[2] = 0x00
        sndBuffer[3] = 0xA9
        sndBuffer[4] = 0x00
        sndBuffer[5] = 0x00
    
        packFormat = "B" * len(sndBuffer)
        tempString = struct.pack(packFormat, *sndBuffer)
        
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
        s.sendto(tempString, addr)
        
        inputs = [s]
        
        ue9s = {}
        
        listen = True
        while listen:
            #We will wait 2 seconds for a response from a Ue9
            rs,ws,es = select.select(inputs, [], [], 1)
            listen = False
            for r in rs:
                if r is s:
                    data,addr = s.recvfrom(38)
                    ue9s[addr[0]] = data
                    listen = True
        s.close()
        
        for ip, data in ue9s.items():
            data = list(struct.unpack("B"*38, data))
            ue9 = { 'LocalID' : data[8], 'PowerLevel' : data[9] , 'IPAddress' : parseIpAddress(data[10:14]), 'Gateway' : parseIpAddress(data[14:18]), 'Subnet' : parseIpAddress(data[18:23]), 'PortA' : struct.unpack("<H", struct.pack("BB", *data[22:24]))[0], 'PortB' : struct.unpack("<H", struct.pack("BB", *data[24:26]))[0], 'DHCPEnabled' : bool(data[26]), 'ProductID' : data[27], 'MACAddress' : "%02X:%02X:%02X:%02X:%02X:%02X" % (data[33], data[32], data[31], data[30], data[29], data[28]), 'SerialNumber' : struct.unpack("<I", struct.pack("BBBB", data[28], data[29], data[30], 0x10))[0], 'HWVersion' : "%s.%s" % (data[35], data[34]), 'CommFWVersion' : "%s.%s" % (data[37], data[36])}
            ue9s[ip] = ue9
        
        return ue9s

    def controlConfig(self, PowerLevel = None, FIODir = None, FIOState = None, EIODir = None, EIOState = None, CIODirection = None, CIOState = None, MIODirection = None, MIOState = None, DoNotLoadDigitalIODefaults = None, DAC0Enable = None, DAC0 = None, DAC1Enable = None, DAC1 = None):
        """
        Name: UE9.controlConfig(PowerLevel = None, FIODir = None, 
              FIOState = None, EIODir = None,
              EIOState = None, CIODirection = None, CIOState = None,
              MIODirection = None, MIOState = None, 
              DoNotLoadDigitalIODefaults = None, DAC0Enable = None, 
              DAC0 = None, DAC1Enable = None, DAC1 = None)
        Args: PowerLevel, 0 = Fixed High, 48 MHz, 1 = Fixed low, 6 MHz
              FIODir, Direction of FIOs
              FIOState, State of FIOs
              EIODir, Direction of EIOs
              EIOState, State of EIOs
              CIODirection, Direction of CIOs (max of 4)
              CIOState, State of CIOs (max of 4)
              MIODirection, Direction of MIOs (max of 3)
              MIOState, Direction of MIOs (max of 3)
              DoNotLoadDigitalIODefaults, Set True, to not load the defaults
              DAC0Enable, True = DAC0 Enabled, False = DAC0 Disabled
              DAC0, The default value for DAC0
              DAC1Enable, True = DAC1 Enabled, False = DAC1 Disabled
              DAC1, The default value for DAC1
        Desc: Configures various parameters associated with the Control
              processor. Affects only the power-up values, not current 
              state. See section 5.3.2 of the User's Guide.
        
        >>> myUe9 = ue9.UE9()
        >>> myUe9.open()
        >>> myUe9.controlConfig()
        {'CIODirection': 0,
         'CIOState': 0,
         'ControlBLVersion': '1.12',
         'ControlFWVersion': '1.97',
         'DAC0': 0,
         'DAC0 Enabled': False,
         'DAC1': 0,
         'DAC1 Enabled': False,
         'EIODir': 0,
         'EIOState': 0,
         'FIODir': 0,
         'FIOState': 0,
         'HiRes Flag': False,
         'MIODirection': 0,
         'MIOState': 0,
         'PowerLevel': 0,
         'ResetSource': 119}
        """
        command = [ 0 ] * 18
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x06
        command[3] = 0x08
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        #command[6] = Writemask. Set it along the way.
        
        if PowerLevel != None:
            command[6] |= 1
            command[7] = PowerLevel
        
        if FIODir != None:
            command[6] |= (1 << 1)
            command[8] = FIODir
        
        if FIOState != None:
            command[6] |= (1 << 1)
            command[9] = FIOState
        
        if EIODir != None:
            command[6] |= (1 << 1)
            command[10] = EIODir
        
        if EIOState != None:
            command[6] |= (1 << 1)
            command[11] = EIOState
        
        if CIODirection != None:
            command[6] |= (1 << 1)
            command[12] = ( CIODirection & 0xf) << 4
        
        if CIOState != None:
            command[6] |= (1 << 1)
            command[12] |= ( CIOState & 0xf )
        
        if DoNotLoadDigitalIODefaults != None:
            command[6] |= (1 << 1)
            if DoNotLoadDigitalIODefaults:
                command[13] |= (1 << 7)
        
        if MIODirection != None:
            command[6] |= (1 << 1)
            command[13] |= ( MIODirection & 7 ) << 4
        
        if MIOState != None:
            command[6] |= (1 << 1)
            command[13] |= ( MIOState & 7 )
        
        if DAC0Enable != None:
            command[6] |= (1 << 2)
            if DAC0Enable:
                command[15] = (1 << 7)
        
        if DAC0 != None:
            command[6] |= (1 << 2)
            command[14] = DAC0 & 0xff
            command[15] |= (DAC0 >> 8 ) & 0xf
        
        if DAC1Enable != None:
            command[6] |= (1 << 2)
            if DAC1Enable:
                command[17] = (1 << 7)
        
        if DAC1 != None:
            command[6] |= (1 << 2)
            command[16] = DAC1 & 0xff
            command[17] |= (DAC1 >> 8 ) & 0xf
        
        result = self._writeRead(command, 24, [ 0xF8, 0x09, 0x08 ])
        
        self.powerLevel = result[7]
        self.controlFWVersion = "%s.%s" % (result[10], result[9])
        self.controlBLVersion = "%s.%s" % (result[12], result[11])
        self.hiRes = bool(result[13] & 1)
        
        self.deviceName = 'UE9'
        if self.hiRes:
            self.deviceName = 'UE9-Pro'
        
        return { 'PowerLevel' : self.powerLevel, 'ResetSource' : result[8], 'ControlFWVersion' : self.controlFWVersion, 'ControlBLVersion' : self.controlBLVersion, 'HiRes Flag' : self.hiRes, 'FIODir' : result[14], 'FIOState' : result[15], 'EIODir' : result[16], 'EIOState' : result[17], 'CIODirection' : (result[18] >> 4) & 0xf, 'CIOState' : result[18] & 0xf, 'MIODirection' : (result[19] >> 4) & 7, 'MIOState' : result[19] & 7, 'DAC0 Enabled' : bool(result[21] >> 7 & 1), 'DAC0' : (result[21] & 0xf) + result[20], 'DAC1 Enabled' : bool(result[23] >> 7 & 1), 'DAC1' : (result[23] & 0xf) + result[22], 'DeviceName' : self.deviceName }
        
    def feedback(self, FIOMask = 0, FIODir = 0, FIOState = 0, EIOMask = 0, EIODir = 0, EIOState = 0, CIOMask = 0, CIODirection = 0, CIOState = 0, MIOMask = 0, MIODirection = 0, MIOState = 0, DAC0Update = False, DAC0Enabled = False, DAC0 = 0, DAC1Update = False, DAC1Enabled = False, DAC1 = 0, AINMask = 0, AIN14ChannelNumber = 0, AIN15ChannelNumber = 0, Resolution = 0, SettlingTime = 0, AIN1_0_BipGain = 0, AIN3_2_BipGain = 0, AIN5_4_BipGain  = 0, AIN7_6_BipGain = 0, AIN9_8_BipGain = 0, AIN11_10_BipGain = 0, AIN13_12_BipGain = 0, AIN15_14_BipGain = 0):
        """
        Name: UE9.feedback(FIOMask = 0, FIODir = 0, FIOState = 0,
              EIOMask = 0, EIODir = 0, EIOState = 0, CIOMask = 0,
              CIODirection = 0, CIOState = 0, MIOMask = 0, MIODirection = 0,
              MIOState = 0, DAC0Update = False, DAC0Enabled = None,
              DAC0 = None, DAC1Update = False, DAC1Enabled = None, DAC1 = None,
              AINMask = 0, AIN14ChannelNumber = 0, AIN15ChannelNumber = 0,
              Resolution = 0, SettlingTime = 0, AIN1_0_BipGain = 0,
              AIN3_2_BipGain = 0, AIN5_4_BipGain  = 0, AIN7_6_BipGain = 0,
              AIN9_8_BipGain = 0, AIN11_10_BipGain = 0, AIN13_12_BipGain = 0,
              AIN15_14_BipGain = 0)
        Args: See section 5.3.3 of the User's Guide
        Desc: A very useful function that writes/reads almost every I/O on the
              LabJack UE9. See section 5.3.3 of the User's Guide.

        >>> myUe9 = ue9.UE9()
        >>> myUe9.open()
        >>> myUe9.feedback()
        {'AIN0': 0, ...
         'TimerB': 0,
         'TimerC': 0}
        """
        command = [ 0 ] * 34
        
        #command[0] = Checksum8
        command[1] = 0xF8
        command[2] = 0x0E
        command[3] = 0x00
        #command[4] = Checksum16 (LSB)
        #command[5] = Checksum16 (MSB)
        command[6] = FIOMask
        command[7] = FIODir
        command[8] = FIOState
        command[9] = EIOMask
        command[10] = EIODir
        command[11] = EIOState
        command[12] = CIOMask
        command[13] = (CIODirection & 0xf) << 4
        command[13] |= (CIOState & 0xf)
        command[14] = MIOMask
        command[15] = (MIODirection & 7) << 4
        command[15] |= (MIOState & 7 )
        
        if DAC0Update:
            if DAC0Enabled:
                command[17] = 1 << 7
            command[17] |= 1 << 6
            
            command[16] = DAC0 & 0xff
            command[17] |= (DAC0 >> 8) & 0xf
        
        if DAC0Update:
            if DAC0Enabled:
                command[19] = 1 << 7
            command[19] |= 1 << 6
            
            command[18] = DAC0 & 0xff
            command[19] |= (DAC0 >> 8) & 0xf
        
        command[20] = AINMask & 0xff
        command[21] = (AINMask >> 8) & 0xff
        command[22] = AIN14ChannelNumber
        command[23] = AIN15ChannelNumber
        command[24] = Resolution
        command[25] = SettlingTime
        command[26] = AIN1_0_BipGain
        command[27] = AIN3_2_BipGain
        command[28] = AIN5_4_BipGain
        command[29] = AIN7_6_BipGain
        command[30] = AIN9_8_BipGain
        command[31] = AIN11_10_BipGain
        command[32] = AIN13_12_BipGain
        command[33] = AIN15_14_BipGain
    
        result = self._writeRead(command, 64, [ 0xF8, 0x1D, 0x00])
        
        return { 'FIODir' : result[6], 'FIOState' : result[7], 'EIODir' : result[8], 'EIOState' : result[9], 'CIODir' : (result[10] >> 4) & 0xf, 'CIOState' : result[10] & 0xf, 'MIODir' : (result[11] >> 4) & 7, 'MIOState' : result[11] & 7, 'AIN0' : unpackShort(result[12:14]), 'AIN1' : unpackShort(result[14:16]), 'AIN2' : unpackShort(result[16:18]), 'AIN3' : unpackShort(result[18:20]), 'AIN4' : unpackShort(result[20:22]), 'AIN5' : unpackShort(result[22:24]), 'AIN6' : unpackShort(result[24:26]), 'AIN7' : unpackShort(result[26:28]), 'AIN8' : unpackShort(result[28:30]), 'AIN9' : unpackShort(result[30:32]), 'AIN10' : unpackShort(result[32:34]), 'AIN11' : unpackShort(result[34:36]), 'AIN12' : unpackShort(result[36:38]), 'AIN13' : unpackShort(result[38:40]), 'AIN14' : unpackShort(result[40:42]), 'AIN15' : unpackShort(result[42:44]), 'Counter0' : unpackInt(result[44:48]), 'Counter1' : unpackInt(result[48:52]), 'TimerA' : unpackInt(result[52:56]), 'TimerB' : unpackInt(result[56:60]), 'TimerC' : unpackInt(result[60:]) }

    digitalPorts = [ 'FIO', 'EIO', 'CIO', 'MIO' ]
    def singleIO(self, IOType, Channel, Dir = None, BipGain = None, State = None, Resolution = None, DAC = 0, SettlingTime = 0):
        """
        Name: UE9.singleIO(IOType, Channel, Dir = None, BipGain = None, State = None, Resolution = None, DAC = 0, SettlingTime = 0)
        Args: See section 5.3.4 of the User's Guide
        Desc: An alternative to Feedback, is this function which writes or
              reads a single output or input. See section 5.3.4 of the User's
              Guide.
              
        >>> myUe9 = ue9.UE9()
        >>> myUe9.open()
        >>> myUe9.singleIO(1, 0, Dir = 1, State = 0)
        {'FIO0 Direction': 1, 'FIO0 State': 0}
        """
        command = [ 0 ] * 8
        
        #command[0] = Checksum8
        command[1] = 0xA3
        command[2] = IOType
        command[3] = Channel
        
        if IOType == 0:
            #Digital Bit Read
            pass
        elif IOType == 1:
            #Digital Bit Write
            if Dir == None or State == None:
                raise LabJackException("Need to specify a direction and state")
            command[4] = Dir
            command[5] = State
        elif IOType == 2:
            #Digital Port Read
            pass
        elif IOType == 3:
            #Digital Port Write
            if Dir == None or State == None:
                raise LabJackException("Need to specify a direction and state")
            command[4] = Dir
            command[5] = State
        elif IOType == 4:
            #Analog In
            if BipGain == None or Resolution == None or SettlingTime == None:
                raise LabJackException("Need to specify a BipGain, Resolution, and SettlingTime")
            command[4] = BipGain
            command[5] = Resolution
            command[6] = SettlingTime
        elif IOType == 5:
            #Analog Out
            if DAC == None:
                raise LabJackException("Need to specify a DAC Value")
            command[4] = DAC & 0xff
            command[5] = (DAC >> 8) & 0xf
        
        result = self._writeRead(command, 8, [ 0xA3 ])
        
        if result[2] == 0:
            #Digital Bit Read
            return { "FIO%s State" % result[3] : result[5], "FIO%s Direction" % result[3] : result[4] }
        elif result[2] == 1:
            #Digital Bit Write
            return { "FIO%s State" % result[3] : result[5], "FIO%s Direction" % result[3] : result[4] }
        elif result[2] == 2:
            #Digital Port Read
            return { "%s Direction" % self.digitalPorts[result[3]] : result[4], "%s State" % self.digitalPorts[result[3]] : result [5] }
        elif result[2] == 3:
            #Digital Port Write
            return { "%s Direction" % self.digitalPorts[result[3]] : result[4], "%s State" % self.digitalPorts[result[3]] : result [5] }
        elif result[2] == 4:
            #Analog In
            ain = (result[6] << 16) + (result[5] << 8) + result[4]
            return { "AIN%s" % result[3] : ain }
        elif result[2] == 5:
            #Analog Out
            dac = (result[6] << 16) + (result[5] << 8) + result[4]
            return { "DAC%s" % result[3] : dac }
    
    def timerCounter(self):
        pass
    
    
    
        
        
        
        
        
        
        
        