"""
A class to make working with the DCA-10 easier. More info on the DCA-10 here:

http://labjack.com/support/dca-10/datasheet
"""
import LabJackPython, u3, u6, ue9

U3_WIRING_DESCRIPTION = """
Connection on DCA-10 -> Connection on LabJack
IN1 -> FIO5
IN2 -> FIO4
EN  -> FIO6
GND -> GND
CS  -> AIN0/FIO0
"""

U6_AND_UE9_WIRING_DESCRIPTION = """
Connection on DCA-10 -> Connection on LabJack
IN1 -> FIO1
IN2 -> FIO0
EN  -> FIO2
GND -> GND
CS  -> AIN0
"""

U6_AND_UE9_WITH_ENCODER_WIRING_DESCRIPTION = """
Connection on DCA-10 -> Connection on LabJack
IN1      -> EIO1
IN2      -> FIO2
EN       -> EIO0
GND      -> GND
CS       -> AIN0

Encoder1 -> FIO0
Encoder2 -> FIO2
Power    -> VS
GND      -> GND
"""

class DCA10Exception(Exception): pass

class NoDevicesConnectedException(DCA10Exception): pass

class InvalidConfigurationException(DCA10Exception): pass

class DCA10(object):
    """
    The DCA10 Class provides a nice interface for working with the DCA-10 motor
    controller and a LabJack. For an example of how to use this class see 
    dca10Example.py.
    """
    def __init__(self, devType = None, encoderAttached = False):
        """
        Name: DAC10.__init__(devType = None, encoderAttached = False)
        
        Args: devType, set to 3 to force use of U3, 6 for U6, 9 for UE9.
              encoderAttached, set to True if your motor has a quadrature 
              encoder output and you want to use it. Note: This requires the 
              use of the EIOs so a CB15 is required. Also, the U3 only has two
              timers and is therefore incapable of doing both the PWM to the 
              DCA and Quadrature.
        
        Desc: Makes a new instance of the DCA10 class.
        
        Examples:
        
        To open the first found device, without an encoder:
        >>> import dca10
        >>> d = dca10.DCA10()
        
        To open the first found U6, without an encoder:
        >>> import dca10
        >>> d = dca10.DCA10(devType = 6)
        
        To open the first found UE9, with an encoder:
        >>> import dca10
        >>> d = dca10.DCA10(devType = 6, encoderAttached = True)
        """
        
        self.device = None
        self.encoderAttached = encoderAttached
        self.directionLine = None
        self.enableLine = None
        self.currentLine = None
        
        self.enableState = 1
        self.directionState = 1
        
        if devType is None:
            if len(LabJackPython.listAll(3)) != 0:
                self.device = u3.U3()
            elif len(LabJackPython.listAll(6)) != 0:
                self.device = u6.U6()
            elif len(LabJackPython.listAll(9)) != 0:
                self.device = ue9.UE9()
            else:
                raise NoDevicesConnectedException("Couldn't find any connected devices. Please connect a LabJack and try again.")
        elif devType == 3:
            self.device = u3.U3()
        elif devType == 6:
            self.device = u6.U6()
        elif devType == 9:
            self.device = ue9.UE9()
        else:
            raise InvalidConfigurationException("Invalid device type submitted. Got %s expected 3, 6, or 9." % devType)
            
        if self.device.devType == 3 and self.encoderAttached:
            raise InvalidConfigurationException("The U3 does not have enough timers to support an encoder.")
        
        if self.device.devType == 3:
            self.directionLine = 5
            self.enableLine = 6
            self.currentLine = 0
        else:
            if self.encoderAttached:
                self.directionLine = 9
                self.enableLine = 8
            else:
                self.directionLine = 1
                self.enableLine = 2
            self.currentLine = 0
                    
        
        # Make sure all the pins are digital, and enable a timer.
        if self.device.devType == 3:
            self.device.writeRegister(50590, 1)
        
        if self.device.devType == 9:
            self.device.writeRegister(7000, 1)
        else:
            self.device.writeRegister(7000, 2)
            
        self.device.writeRegister(7002, 1)
        
        
        # Set the Timer for PWM and Duty Cycle of 0%
        if self.encoderAttached:
            self.device.writeRegister(50501, 3)
            self.device.writeRegister(7100, [8, 0, 8, 0, 0, 65535])
        else:
            self.device.writeRegister(50500, 0)
            self.device.writeRegister(50501, 1)
            self.device.writeRegister(7100, [0, 65535])
        
        # Set the direction and enable lines to output.
        # Don't have to do this because modbus will take care of direction.
        #self.device.writeRegister(6100 + self.enableLine, 1)
        #self.device.writeRegister(6100 + self.directionLine, 1)
        
        
        # Set the direction and enable lines high.
        self.device.writeRegister(6000 + self.enableLine, 1)
        self.device.writeRegister(6000 + self.directionLine, 1)
        
    def startMotor(self, dutyCycle = 1):
        """
        Name: DCA10.startMotor(dutyCycle = 1)
        
        Args: dutyCycle, a value between 0-1 representing the duty cycle of the 
              PWM output. ( Controls how fast the motor spins ).
              
        Desc: Starts the motor at the specified duty cycle.
              By default, will start the motor with a 100% duty cycle.
        
        Example:
        >>> import dca10
        >>> d = dca10.DCA10()
        >>> d.startMotor(dutyCycle = 0.5) 
        """
        if dutyCycle < 0 or dutyCycle > 1:
            raise InvalidConfigurationException("Duty cycle must be between 0 and 1. Got %s." % dutyCycle)
        
        value = int(65535 - (65535 * dutyCycle))
        if self.encoderAttached:
            self.device.writeRegister(7104, [0, value])
        else:
            self.device.writeRegister(7100, [0, value])
        
        if not self.enableState:
            self.device.writeRegister(6000 + self.enableLine, 1)
            
    def stopMotor(self):
        """
        Name: DCA10.stopMotor()
        
        Args: None
        
        Desc: Sets the enable line low, stopping the motor.
        
        Example:
        >>> import dca10
        >>> d = dca10.DCA10()
        >>> d.startMotor(dutyCycle = 0.5) 
        >>> d.stopMotor()
        """
        self.device.writeRegister(6000 + self.enableLine, 0)
        self.enableState = 0
        
    def toggleDirection(self):
        """
        Name: DCA10.toggleDirection()
        
        Args: None
        
        Desc: Toggles the direction line, which causes the motor to change
              directions.
              
        Example:
        >>> import dca10
        >>> d = dca10.DCA10()
        >>> d.startMotor(dutyCycle = 0.5) 
        >>> d.toggleDirection()
        """
        self.directionState = not self.directionState
        self.device.writeRegister(6000 + self.directionLine, self.directionState)
        
    def readCurrent(self):
        """
        Name: DCA10.readCurrent()
        
        Args: None
        
        Desc: Takes a sample off the CS line and applies the offset from the
              DCA-10 datasheet. Returns a floating point value representing 
              Amps.
              
        Example:
        >>> import dca10
        >>> d = dca10.DCA10()
        >>> d.startMotor(dutyCycle = 0.5) 
        >>> print d.readCurrent()
        0.018158430290222165
        """
        return (self.device.readRegister(0 + self.currentLine) * 3.7596 )
    
    def readEncoder(self):
        """
        Name: DCA10.readEncoder()
        
        Args: None
        
        Desc: Reads the current value of the quadrature encoder. Raises a 
              DCA10Exception if the encoder is not attached.
              
        Example:
        >>> import dca10
        >>> d = dca10.DCA10(encoderAttached = True)
        >>> d.startMotor(dutyCycle = 0.5) 
        >>> print d.readEncoder()
        3925
        """
        if self.encoderAttached:
            return self.device.readRegister(7200)
        else:
            raise DCA10Exception("You cannot read the Quadrature Encoder when it is not connected.")
    
    def wiringDescription(self):
        """
        Name: DCA10.wiringDescription()
        
        Args: None
        
        Desc: Returns a string that describes how the DCA-10 should be wired to
              the LabJack.
              
        Example:
        >>> import dca10
        >>> d = dca10.DCA10(devType = 6)
        >>> print d.wiringDescription()
        
        Connection on DCA-10 -> Connection on LabJack
        IN1 -> FIO1
        IN2 -> FIO0
        EN  -> FIO2
        GND -> GND
        CS  -> AIN0
        """
        if self.device.devType == 3:
            return U3_WIRING_DESCRIPTION
        elif self.encoderAttached:
            return U6_AND_UE9_WITH_ENCODER_WIRING_DESCRIPTION
        else:
            return U6_AND_UE9_WIRING_DESCRIPTION