"""
Name: LJTickDAC
Desc: A simple GUI application to demonstrate the usage of the I2C and
LabJack Python modules to set the value of DACA and DACB in a LJ-TickDAC
"""
import struct
import sys
import threading
import time

try:
    import Tkinter
except ImportError: # Python 3
    import tkinter as Tkinter

try:
    import tkMessageBox
except ImportError: # Python 3
    import tkinter.messagebox as tkMessageBox

# Attempt to load the labjack driver
try:
    import LabJackPython
    import u3
    import u6
    import ue9
except:
    tkMessageBox.showerror("Driver error", "The driver could not be imported.\nIf you are on windows, please install the UD driver from www.labjack.com")
    sys.exit(1)

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

class LJTickDAC(Tkinter.Tk):
    """
    Name: LJTickDAC
    Desc: A simple GUI application to demonstrate the usage of the I2C and
    LabJack Python modules to set the value of DACA and DACB in a LJ-TickDAC
    """
    U3 = 3
    U6 = 6
    UE9 = 9
    AUTO = 0
    FONT_SIZE = 10
    FONT = "Arial"
    AIN_PIN_DEFAULT = -1 # AIN must be configured
    DAC_PIN_DEFAULT = 0
    U3_DAC_PIN_OFFSET = 4
    EEPROM_ADDRESS = 0x50
    DAC_ADDRESS = 0x12
    
    def __init__(self):
        # Create the window
        Tkinter.Tk.__init__(self)
        self.title("LJTickDAC")

        # Create and place labels
        Tkinter.Label(self, text="Serial Num:", font=(LJTickDAC.FONT, LJTickDAC.FONT_SIZE)).grid(row=0, column=0, sticky=Tkinter.W)
        self.serialDisplay = Tkinter.Label(self, font=(LJTickDAC.FONT, LJTickDAC.FONT_SIZE), text="please wait...",)
        self.serialDisplay.grid(row=0, column=1, sticky=Tkinter.W)
        Tkinter.Label(self, text="DAC A:", font=(LJTickDAC.FONT, LJTickDAC.FONT_SIZE)).grid(row=1, column=0, sticky=Tkinter.W)
        Tkinter.Label(self, text="DAC B:", font=(LJTickDAC.FONT, LJTickDAC.FONT_SIZE)).grid(row=2, column=0, sticky=Tkinter.W)
        self.ainALabel = Tkinter.Label(self, text="AIN:", font=(LJTickDAC.FONT, LJTickDAC.FONT_SIZE))
        self.ainALabel.grid(row=3, column=0, sticky=Tkinter.W)
        self.ainDisplay = Tkinter.Label(self, text="not configured", font=(LJTickDAC.FONT, LJTickDAC.FONT_SIZE))
        self.ainDisplay.grid(row=3, column=1, sticky=Tkinter.W)

        # Create and place entry boxes
        self.dacAEntry = Tkinter.Entry(self, font=(LJTickDAC.FONT, LJTickDAC.FONT_SIZE))
        self.dacAEntry.grid(row=1, column=1, sticky=Tkinter.E+Tkinter.W)
        self.dacBEntry = Tkinter.Entry(self, font=(LJTickDAC.FONT, LJTickDAC.FONT_SIZE))
        self.dacBEntry.grid(row=2, column=1, sticky=Tkinter.E+Tkinter.W)

        # Create and place buttons
        Tkinter.Button(self, text="Setup", command=self.showSetup, font=(LJTickDAC.FONT, LJTickDAC.FONT_SIZE)).grid(row=4, column=0, sticky=Tkinter.W)
        Tkinter.Button(self, text="Apply Changes", font=(LJTickDAC.FONT, LJTickDAC.FONT_SIZE), comman=self.updateDevice).grid(row=4, column=1, sticky=Tkinter.E+Tkinter.W)
        Tkinter.Label(self, text="(c) 2009 Labjack Corp.                         ", font=(LJTickDAC.FONT, LJTickDAC.FONT_SIZE)).grid(row=5, column=0, columnspan=2, sticky=Tkinter.W, padx=1, pady=1)

        # Set defaults
        self.ainPin = LJTickDAC.AIN_PIN_DEFAULT
        self.dacPin = LJTickDAC.DAC_PIN_DEFAULT

        # Create a variable for the ain read thread
        self.ainReadThread = None

        # load the devices
        self.loadFirstDevice()

        # Organize cleanup
        self.protocol("WM_DELETE_WINDOW", self.cleanUp)

        # Show settings window
        self.searchForDevices()
        settingsWindow = SettingsWindow(self, self.deviceType, self.dacPin, self.ainPin, self.u3Available, self.u6Available, self.ue9Available)
        try: settingsWindow.attributes('-topmost', True)
        except: pass
        
    def updateDevice(self):
        """
        Name: updateDevice()
        Desc: Changes DACA and DACB to the amounts specified by the user
        """
        # Determine pin numbers
        if self.deviceType == self.U3:
            sclPin = self.dacPin + LJTickDAC.U3_DAC_PIN_OFFSET
            sdaPin = sclPin + 1
        else:
            sclPin = self.dacPin
            sdaPin = sclPin + 1

        # Get voltage for DACA
        try:voltageA = float(self.dacAEntry.get())
        except:
            self.showErrorWindow("Invalid entry", "Please enter a numerical value for DAC A")
            return

        # Get voltage DACB
        try:voltageB = float(self.dacBEntry.get())
        except:
            self.showErrorWindow("Invalid entry", "Please enter a numerical value for DAC B")
            return

        # Make requests
        try:
            self.device.i2c(LJTickDAC.DAC_ADDRESS, [48, int(((voltageA*self.aSlope)+self.aOffset)/256), int(((voltageA*self.aSlope)+self.aOffset)%256)], SDAPinNum = sdaPin, SCLPinNum = sclPin)
            self.device.i2c(LJTickDAC.DAC_ADDRESS, [49, int(((voltageB*self.bSlope)+self.bOffset)/256), int(((voltageB*self.bSlope)+self.bOffset)%256)], SDAPinNum = sdaPin, SCLPinNum = sclPin)
        except:
            self.showErrorWindow("I2C Error", "Whoops! Something went wrong when setting the LJTickDAC. Is the device detached?\n\nPython error:" + str(sys.exc_info()[1]))
            self.showSetup()
            
    def searchForDevices(self):
        """
        Name: searchForDevices()
        Desc: Determines which devices are available
        """
        self.u3Available = len(LabJackPython.listAll(LJTickDAC.U3)) > 0
        self.u6Available = len(LabJackPython.listAll(LJTickDAC.U6)) > 0
        self.ue9Available = len(LabJackPython.listAll(LJTickDAC.UE9)) > 0
        
    def loadFirstDevice(self):
        """
        Name: loadFirstDevice()
        Desc: Determines which devices are available and loads the first one found
        """
        try:

            self.searchForDevices()
            
            # Determine which device to use
            if self.u3Available: self.deviceType = LJTickDAC.U3
            elif self.u6Available: self.deviceType = LJTickDAC.U6
            elif self.ue9Available: self.deviceType = LJTickDAC.UE9
            else:
                self.showErrorWindow("Fatal Error", "No LabJacks were found to be connected to your computer.\nPlease check your wiring and try again.")
                sys.exit()

            self.loadDevice(self.deviceType)
            
        except:
            self.showErrorWindow("Fatal Error - First Load", "Python error:" + str(sys.exc_info()[1]))
            sys.exit()

    def loadDevice(self, deviceType):
        """
        Name: loadDevice(deviceType)
        Desc: loads the first device of device type
        """

        self.deviceType = deviceType
        
        # Determine which device to use
        if self.deviceType == LJTickDAC.U3:
            self.device = u3.U3()
        elif self.deviceType == LJTickDAC.U6:
            self.device = u6.U6()
        else:
            self.device = ue9.UE9()
            
        # Display serial number
        self.serialDisplay.config(text=self.device.serialNumber)

        # Configure pins if U3
        if self.deviceType == LJTickDAC.U3:
            self.device.configIO(FIOAnalog=15, TimerCounterPinOffset=8) # Configures FIO0-2 as analog
        
        # Get the calibration constants
        self.getCalConstants()
        
    def showSetup(self):
        """
        Name: showSetup()
        Desc: Display the settings window
        """
        self.searchForDevices()
        SettingsWindow(self, self.deviceType, self.dacPin, self.ainPin, self.u3Available, self.u6Available, self.ue9Available)

    def showErrorWindow(self, title, info):
        """
        Name:showErrorWindow(title, info)
        Desc:Shows an error popup for last exception encountered
        """
        tkMessageBox.showerror(title, str(info))

    def updateSettings(self, deviceType, ainPin, dacPin):
        """
        Name: updateSettings(deviceType, ainPin, dacPin)
        Desc: updates the configuration of the application
        """
        try:
            if self.ainReadThread is not None: self.ainReadThread.stop()
            self.device.close()
            self.ainPin = ainPin
            self.dacPin = dacPin
            self.loadDevice(deviceType)

            if ainPin != -1: # AIN is configured
                self.ainReadThread = AINReadThread(self.ainDisplay, self.device, self.deviceType, self.ainPin)
                self.ainReadThread.start()
            else:
                self.ainDisplay.config(text="disabled")
        except:
            self.showErrorWindow("Update Settings Error", "Python error:" + str(sys.exc_info()[1]))
            sys.exit()

    def cleanUp(self):
        """
        Name: cleanUp()
        Desc: Closes devices, terminates threads, and closes windows
        """
        if self.ainReadThread is not None: self.ainReadThread.stop()
        if self.device is not None: self.device.close()
        self.destroy()

    def getCalConstants(self):
        """
        Name: getCalConstants()
        Desc: Loads or reloads the calibration constants for the LJTic-DAC
              See datasheet for more info
        """
        # Determine pin numbers
        if self.deviceType == LJTickDAC.U3:
            sclPin = self.dacPin + LJTickDAC.U3_DAC_PIN_OFFSET
            sdaPin = sclPin + 1
        else:
            sclPin = self.dacPin
            sdaPin = sclPin + 1

        # Make request
        data = self.device.i2c(LJTickDAC.EEPROM_ADDRESS, [64], NumI2CBytesToReceive=36, SDAPinNum = sdaPin, SCLPinNum = sclPin)
        response = data['I2CBytes']
        self.aSlope = toDouble(response[0:8])
        self.aOffset = toDouble(response[8:16])
        self.bSlope = toDouble(response[16:24])
        self.bOffset = toDouble(response[24:32])

        if 255 in response: self.showErrorWindow("Pins", "The calibration constants seem a little off. Please go into settings and make sure the pin numbers are correct and that the LJTickDAC is properly attached.")
        
class SettingsWindow(Tkinter.Toplevel):
    """
    Name: SettingsWindow
    Desc: A dialog window that allows the user to set the pins and device
    used by the application.
    """

    FONT_SIZE = 12
    FONT = "Arial"
    
    def __init__(self, parent, currentDevice, currentDACPin, currentAINPin, u3Available, u6Available, ue9Available):
        # Create window
        Tkinter.Toplevel.__init__(self, parent)
        self.title("Setup")
        self.parent = parent

        # Create and place labels
        Tkinter.Label(self, text="Device:", font=(LJTickDAC.FONT, LJTickDAC.FONT_SIZE)).grid(row=0, column=0, sticky=Tkinter.W)
        Tkinter.Label(self, text="DAC Pins:", font=(LJTickDAC.FONT, LJTickDAC.FONT_SIZE)).grid(row=1, column=0, sticky=Tkinter.W)
        Tkinter.Label(self, text="AIN Pins:", font=(LJTickDAC.FONT, LJTickDAC.FONT_SIZE)).grid(row=2, column=0, sticky=Tkinter.W)
        Tkinter.Label(self, text="Notice: Settings only take effect after clicking apply. AIN pins are provided for testing.").grid(row=4, column=0, columnspan=2)
        # Create and place radio buttons for the device
        self.deviceVar = Tkinter.IntVar()
        self.deviceVar.set(currentDevice)
        deviceFrame = Tkinter.Frame(self)
        u3Radio = Tkinter.Radiobutton(deviceFrame, text="U3", variable=self.deviceVar, value=LJTickDAC.U3, font=(SettingsWindow.FONT, SettingsWindow.FONT_SIZE), command=self.adjustText)
        u3Radio.grid(row=0, column=0)
        if not u3Available: u3Radio.config(state=Tkinter.DISABLED)
        u6Radio = Tkinter.Radiobutton(deviceFrame, text="U6", variable=self.deviceVar, value=LJTickDAC.U6, font=(SettingsWindow.FONT, SettingsWindow.FONT_SIZE), command=self.adjustText)
        u6Radio.grid(row=0, column=1)
        if not u6Available: u6Radio.config(state=Tkinter.DISABLED)
        ue9Radio = Tkinter.Radiobutton(deviceFrame, text="UE9", variable=self.deviceVar, value=LJTickDAC.UE9, font=(SettingsWindow.FONT, SettingsWindow.FONT_SIZE), command=self.adjustText)
        ue9Radio.grid(row=0, column=2)
        if not ue9Available: ue9Radio.config(state=Tkinter.DISABLED)
        deviceFrame.grid(row=0, column=1, sticky=Tkinter.E+Tkinter.W)

        # Create and place radio buttons for the dac pins
        self.dacPin = Tkinter.IntVar()
        self.dacPin.set(currentDACPin)
        dacPinFrame = Tkinter.Frame(self)
        self.dacOptARadio = Tkinter.Radiobutton(dacPinFrame, text="FIO 0/1", variable=self.dacPin, value=0, font=(SettingsWindow.FONT, SettingsWindow.FONT_SIZE))
        self.dacOptARadio.grid(row=0, column=0)
        self.dacOptBRadio = Tkinter.Radiobutton(dacPinFrame, text="FIO 2/3", variable=self.dacPin, value=2, font=(SettingsWindow.FONT, SettingsWindow.FONT_SIZE))
        self.dacOptBRadio.grid(row=0, column=1)
        dacPinFrame.grid(row=1, column=1, sticky=Tkinter.E+Tkinter.W)

        # Create and place the radio buttons for the ain pins
        self.ainPin = Tkinter.IntVar()
        self.ainPin.set(currentAINPin)
        ainPinFrame = Tkinter.Frame(self)
        Tkinter.Radiobutton(ainPinFrame, text="None", variable=self.ainPin, value=-1, font=(SettingsWindow.FONT, SettingsWindow.FONT_SIZE)).grid(row=0, column=0)
        self.ainOptARadio = Tkinter.Radiobutton(ainPinFrame, text="AIN 0", variable=self.ainPin, value=0, font=(SettingsWindow.FONT, SettingsWindow.FONT_SIZE))
        self.ainOptARadio.grid(row=0, column=1)
        self.ainOptBRadio = Tkinter.Radiobutton(ainPinFrame, text="AIN 2", variable=self.ainPin, value=2, font=(SettingsWindow.FONT, SettingsWindow.FONT_SIZE))
        self.ainOptBRadio.grid(row=0, column=2)
        ainPinFrame.grid(row=2, column=1, sticky=Tkinter.E+Tkinter.W)

        # Create and place apply and cancel buttons
        buttonsFrame = Tkinter.Frame(self)
        Tkinter.Button(buttonsFrame, text="Apply", command=self.applyChanges, font=(SettingsWindow.FONT, SettingsWindow.FONT_SIZE)).grid(row=0, column=0)
        #Button(buttonsFrame, text="Cancel", font=(SettingsWindow.FONT, SettingsWindow.FONT_SIZE)).grid(row=0, column=1)
        buttonsFrame.grid(row=3, column=0, columnspan=2, sticky=Tkinter.E+Tkinter.W)

        # Adjust text for device and prepare for future adjustments
        self.adjustText()
        

    def adjustText(self):
        """
        Name: adjustText()
        Desc: Adjusts the text of the radio buttons depending on the device type selected
        """
        deviceType = self.deviceVar.get()
        if deviceType == LJTickDAC.U3:
            self.dacOptARadio.config(text="FIO 4/5")
            self.dacOptBRadio.config(text="FIO 6/7")
            self.ainOptARadio.config(text="AIN/FIO 0")
            self.ainOptBRadio.config(text="AIN/FIO 2")
        else:
            self.dacOptARadio.config(text="FIO 0/1")
            self.dacOptBRadio.config(text="FIO 2/3")
            self.ainOptARadio.config(text="AIN 0")
            self.ainOptBRadio.config(text="AIN 2")

    def applyChanges(self):
        """
        Name: applyChanges()
        Desc: applys the changes to the application and closes the window
        """
        self.parent.updateSettings(self.deviceVar.get(), self.ainPin.get(), self.dacPin.get())
        self.destroy()

class AINReadThread(threading.Thread):
    """
    Name: AINReadThread
    Desc: A thread that reads from a given analog input every secound and updates a GUI
    """

    def __init__(self, displayLabel, device, deviceType, pinNum):
        threading.Thread.__init__(self)
        self.displayLabel = displayLabel
        self.device = device
        self.pinNum = pinNum
        self.deviceType = deviceType

    def stop(self):
        """
        Name: stop()
        Desc: Stops this thread
        """
        self.running = False

    def run(self):
        """
        Name: run()
        Desc: Starts this thread
        """
        try:
            self.running = True
            while self.running:
                if self.deviceType == LJTickDAC.UE9:
                    # See section 2.7.2 until better calibartion is applied
                    voltage = self.device.feedback(AINMask=5)['AIN'+str(self.pinNum)]/65536.0*5 
                elif self.deviceType == LJTickDAC.U3:
                    voltage = self.device.getAIN(self.pinNum)
                else: voltage = self.device.getAIN(self.pinNum)
                self.displayLabel.config(text=str(voltage))
                time.sleep(1)
        except:
            self.displayLabel.config(text="AIN read error. Device detached?\nClick \"Setup\" to start again...")
        
# Create application
LJTickDAC().mainloop()
