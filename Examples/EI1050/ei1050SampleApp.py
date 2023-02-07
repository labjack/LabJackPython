"""
Name: ei1050SampleApp
Desc: A simple GUI application to demonstrate the usage of the ei1050 and
LabJack Python modules. For an example of using the Labjack Python module
directly look at the source code of ei1050.py

Note: Our Python interfaces throw exceptions when there are any issues with
device communications that need addressed. Many of our examples will
terminate immediately when an exception is thrown. The onus is on the API
user to address the cause of any exceptions thrown, and add exception
handling when appropriate. We create our own exception classes that are
derived from the built-in Python Exception class and can be caught as such.
For more information, see the implementation in our source code and the
Python standard documentation.
"""
import sys

try:
    from Queue import Queue
except ImportError:  # Python 3
    from queue import Queue

try:
    import Tkinter
except ImportError:  # Python 3
    import tkinter as Tkinter

try:
    import tkMessageBox
except ImportError:  # Python 3
    import tkinter.messagebox as tkMessageBox

try:
    import LabJackPython
    import u3
    import u6
    import ue9

    import ei1050
except:
    tkMessageBox.showerror("Driver error", '''The driver could not be imported.
Please install the UD driver (Windows) or Exodriver (Linux and Mac OS X) from www.labjack.com''')


class MainWindow:
    """
    The main window of the application
    """

    FONT_SIZE = 10
    FIO_PIN_STATE = 0  # For U3
    FONT = "Arial"

    def __init__(self):
        # Basic setup
        self.window = Tkinter.Tk()
        self.window.title("EI1050 Sample Application")
        self.readingsFrame = Tkinter.Frame(height=500, width=2000, bd=1, relief=Tkinter.SUNKEN)
        self.readingsFrame.pack(side=Tkinter.LEFT)
        self.buttonsFrame = Tkinter.Frame(height=500, width=500, bd=1, relief=Tkinter.SUNKEN)
        self.buttonsFrame.pack(side=Tkinter.RIGHT)

        # Readings frame
        Tkinter.Label(self.readingsFrame, text="Device Serial Number:", font=(MainWindow.FONT, MainWindow.FONT_SIZE)).grid(row=0, column=0, sticky=Tkinter.W, padx=1, pady=1)
        Tkinter.Label(self.readingsFrame, text="Temperature:", font=(MainWindow.FONT, MainWindow.FONT_SIZE)).grid(row=1, column=0, sticky=Tkinter.W, padx=1, pady=1)
        Tkinter.Label(self.readingsFrame, text="Humidity:", font=(MainWindow.FONT, MainWindow.FONT_SIZE)).grid(row=2, column=0, sticky=Tkinter.W, padx=1, pady=1)
        Tkinter.Label(self.readingsFrame, text="Probe Status:", font=(MainWindow.FONT, MainWindow.FONT_SIZE)).grid(row=3, column=0, sticky=Tkinter.W, padx=1, pady=1)
        Tkinter.Label(self.readingsFrame, text="(c) 2009 Labjack Corp.                         ", font=(MainWindow.FONT, MainWindow.FONT_SIZE)).grid(row=4, column=0, columnspan=2, sticky=Tkinter.W, padx=1, pady=1)

        self.serialDisplay = Tkinter.Label(self.readingsFrame, text="", font=(MainWindow.FONT, MainWindow.FONT_SIZE))
        self.serialDisplay.grid(row=0, column=1, sticky=Tkinter.W, padx=1, pady=1)
        self.tempDisplay = Tkinter.Label(self.readingsFrame, text="", font=(MainWindow.FONT, MainWindow.FONT_SIZE))
        self.tempDisplay.grid(row=1, column=1, sticky=Tkinter.W, padx=1, pady=1)
        self.humidDisplay = Tkinter.Label(self.readingsFrame, text="", font=(MainWindow.FONT, MainWindow.FONT_SIZE))
        self.humidDisplay.grid(row=2, column=1, sticky=Tkinter.W, padx=1, pady=1)
        self.statusDisplay = Tkinter.Label(self.readingsFrame, text="", font=(MainWindow.FONT, MainWindow.FONT_SIZE))
        self.statusDisplay.grid(row=3, column=1, sticky=Tkinter.W, padx=1, pady=1)

        # Buttons frame
        self.startButton = Tkinter.Button(self.buttonsFrame, text="Start", command=self.start, font=(MainWindow.FONT, MainWindow.FONT_SIZE))
        self.startButton.grid(row=0, column=0)
        Tkinter.Label(self.readingsFrame, text="", font=(MainWindow.FONT, MainWindow.FONT_SIZE)).grid(row=2, column=0)
        self.instructionsButton = Tkinter.Button(self.buttonsFrame, text="Instructions", command=self.showInstructions, font=(MainWindow.FONT, MainWindow.FONT_SIZE))
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
            if len(LabJackPython.listAll(3)) > 0:
                self.device = u3.U3()
            elif len(LabJackPython.listAll(6)) > 0:
                self.device = u6.U6()
            else:
                self.device = ue9.UE9()

            self.serialDisplay.config(text=self.device.serialNumber)

            # Create and start the thread
            self.thread = ei1050.EI1050Reader(self.device, self.targetQueue)

            # Start scheduleing
            self.window.after(1000, self.updateLabels)
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
        if self.thread.exception is not None:
            showErrorWindow(self.thread.exception[0], self.thread.exception[1])

        else:
            # Change out the display
            latestReading = None
            while not self.targetQueue.empty():
                latestReading = self.targetQueue.get()

            if latestReading is not None:
                self.tempDisplay.config(text=str(latestReading.getTemperature()) + " deg C")
                self.humidDisplay.config(text=str(latestReading.getHumidity()) + " %")
                self.statusDisplay.config(text=str(latestReading.getStatus()))

            self.window.after(1000, self.updateLabels)

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
            if self.thread is not None:
                self.thread.stop()
                self.thread.join()
            if self.device is not None:
                self.device.close()
        except:
            print("Error terminating app")
        finally:
            self.window.destroy()


def showErrorWindow(title, info):
        """
        Name:showErrorWindow()
        Desc:Shows an error popup for last exception encountered
        """
        tkMessageBox.showerror(title, str(info) + "\n\nPlease check your " +
                               "wiring. If you need help, click instructions.")


MainWindow()
