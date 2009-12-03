"""
Name: ei1050SampleApp
Desc: A simple GUI application to demonstrate the usage of the ei1050 and
LabJack Python modules. For an example of using the Labjack Python module directly
look at the source code of ei1050.py
"""
import sys
from Queue import Queue
from Tkinter import *
import tkMessageBox

try:
    import LabJackPython
    from u3 import *
    from u6 import *
    from ue9 import *
    from ei1050 import *
except:
    tkMessageBox.showerror("Driver error", "The driver could not be imported.\nIf you are on windows, please install the UD driver from www.labjack.com")

class MainWindow:
    """
    The main window of the application
    """

    FONT_SIZE = 10
    FIO_PIN_STATE = 0 # for u3
    FONT = "Arial"

    def __init__(self):
        # Basic setup
        self.window = Tk()
        self.window.title("EI1050 Sample Application")
        self.readingsFrame = Frame(height=500, width=2000, bd=1, relief=SUNKEN)
        self.readingsFrame.pack(side=LEFT)
        self.buttonsFrame = Frame(height=500, width=500, bd=1, relief=SUNKEN)
        self.buttonsFrame.pack(side=RIGHT)

        # Readings frame
        Label(self.readingsFrame, text="Device Serial Number:", font=(MainWindow.FONT, MainWindow.FONT_SIZE)).grid(row=0, column=0, sticky=W, padx=1, pady=1)
        Label(self.readingsFrame, text="Temperature:", font=(MainWindow.FONT, MainWindow.FONT_SIZE)).grid(row=1, column=0, sticky=W, padx=1, pady=1)
        Label(self.readingsFrame, text="Humidity:", font=(MainWindow.FONT, MainWindow.FONT_SIZE)).grid(row=2, column=0, sticky=W, padx=1, pady=1)
        Label(self.readingsFrame, text="Probe Status:", font=(MainWindow.FONT, MainWindow.FONT_SIZE)).grid(row=3, column=0,sticky=W, padx=1, pady=1)
        Label(self.readingsFrame, text="(c) 2009 Labjack Corp.                         ", font=(MainWindow.FONT, MainWindow.FONT_SIZE)).grid(row=4, column=0, columnspan=2, sticky=W, padx=1, pady=1)

        self.serialDisplay = Label(self.readingsFrame, text="", font=(MainWindow.FONT, MainWindow.FONT_SIZE))
        self.serialDisplay.grid(row=0, column=1, sticky=W, padx=1, pady=1)
        self.tempDisplay = Label(self.readingsFrame, text="", font=(MainWindow.FONT, MainWindow.FONT_SIZE))
        self.tempDisplay.grid(row=1, column=1, sticky=W, padx=1, pady=1)
        self.humidDisplay = Label(self.readingsFrame, text="", font=(MainWindow.FONT, MainWindow.FONT_SIZE))
        self.humidDisplay.grid(row=2, column=1, sticky=W, padx=1, pady=1)
        self.statusDisplay = Label(self.readingsFrame, text="", font=(MainWindow.FONT, MainWindow.FONT_SIZE))
        self.statusDisplay.grid(row=3, column=1, sticky=W, padx=1, pady=1)

        # Buttons frame
        self.startButton = Button(self.buttonsFrame, text="Start", command=self.start, font=(MainWindow.FONT, MainWindow.FONT_SIZE))
        self.startButton.grid(row=0, column=0)
        Label(self.readingsFrame, text="", font=(MainWindow.FONT, MainWindow.FONT_SIZE)).grid(row=2, column=0)
        self.instructionsButton = Button(self.buttonsFrame, text="Instructions", command=self.showInstructions, font=(MainWindow.FONT, MainWindow.FONT_SIZE))
        self.instructionsButton.grid(row=2, column=0)
        #self.deviceSelection = StringVar(self.window)
        #self.deviceSelection.set("U3")
        #OptionMenu(self.buttonsFrame, self.deviceSelection, "U3", "U6", "UE9").grid(row=2, column=0)

        # Ensure the exsistance of a thread, queue, and device variable
        self.targetQueue = Queue()
        self.thread = None
        self.device = None

        # Determine if we are reading data
        self.reading = False
        
        # Start mainloop
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.mainloop()
        
    def start(self):
        """
        Name:MainWindow.start()
        Desc:Starts reading values from EI1050 probe
        """
        try:
            # Get device selection
            #if self.deviceSelection.get() == "U3": self.device = U3()
            #elif self.deviceSelection.get() == "U6": self.device = U6()
            #else: self.device = UE9()
            if len(LabJackPython.listAll(3)) > 0: self.device = U3()
            elif len(LabJackPython.listAll(6)) > 0: self.device = U6()
            else: self.device = UE9()
            
            self.serialDisplay.config(text=self.device.serialNumber)
            #if self.deviceSelection.get() == "U6" or self.deviceSelection.get() == "U3": self.device.setToFactoryDefaults()

            #if len(LabJackPython.listAll(3)) > 0:
            #    print MainWindow.FIO_PIN_STATE
            #    self.device.configU3(FIOAnalog = MainWindow.FIO_PIN_STATE)
            # Create and start the thread
            self.thread = EI1050Reader(self.device, self.targetQueue)

            # Start scheduleing
            self.window.after(1000,self.updateLabels)
            self.thread.start()

            # Change button
            self.startButton.config(text="Stop", command=self.stop)
        except:
            showErrorWindow(sys.exc_info()[0], sys.exc_info()[1])
        
    def stop(self):
        """
        Name:MainWindow.stop()
        Desc: Stops reading values from EI1050 probe
        """
        self.thread.stop()
        self.thread.join()
        self.device.close()
        self.startButton.config(text="Start", command=self.start)

    def updateLabels(self):
        """
        Name:MainWindow.updateLabels()
        Desc: Gets the latest reading from the readings queue and display it
        """
        # Check for errors
        if self.thread.exception != None:
            showErrorWindow(self.thread.exception[0], self.thread.exception[1])

        else:   
            # Change out the display
            latestReading = None
            while not self.targetQueue.empty():
                latestReading = self.targetQueue.get()

            if latestReading != None:
                self.tempDisplay.config(text = str(latestReading.getTemperature()) + " deg C")
                self.humidDisplay.config(text = str(latestReading.getHumidity()) + " %")
                self.statusDisplay.config(text = str(latestReading.getStatus()))

            self.window.after(1000,self.updateLabels)

    def showInstructions(self):
        tkMessageBox.showinfo("Instructions", '''U3 SHT configured with pins as follows:
Green(Data) -- FIO4             
White(Clock) -- FIO5             
Black(GND) -- GND             
Red(Power) -- FIO7             
Brown(Enable) -- FIO7

U6/UE9 SHT configured with pins as follows:
Green(Data) -- FIO0             
White(Clock) -- FIO1             
Black(GND) -- GND             
Red(Power) -- FIO3             
Brown(Enable) -- FIO3''')

    def close(self):
        try:
            if self.thread != None:
                self.thread.stop()
                self.thread.join()
            if self.device != None:
                self.device.close()
        except: print "error terminating app"
        finally:
            self.window.destroy()
            
def showErrorWindow(title, info):
        """
        Name:showErrorWindow()
        Desc:Shows an error popup for last exception encountered
        """
        tkMessageBox.showerror(title, str(info) + "\n\nPlease check your wiring. If you need help, click instructions.")
        
MainWindow()
