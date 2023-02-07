"""
An example program to show you how easy it is to work with Modbus on a LabJack
U3, U6 or UE9.

Note: The UD-Modbus interface is deprecated.

Our Python interfaces throw exceptions when there are any issues with
device communications that need addressed. Many of our examples will
terminate immediately when an exception is thrown. The onus is on the API
user to address the cause of any exceptions thrown, and add exception
handling when appropriate. We create our own exception classes that are
derived from the built-in Python Exception class and can be caught as such.
For more information, see the implementation in our source code and the
Python standard documentation.
"""
import random

import u3
import u6
import ue9


if __name__ == '__main__':
    print("This program shows how to work with Modbus and your LabJack U3, U6 or UE9. Registers are taken directly from the Modbus map (https://labjack.com/support/software/api/modbus/ud-modbus).\n")

    print("Opening device.\n")
    # Comment and uncomment below code based on the LabJack you are using.
    # By default the U3 is opened.
    d = u3.U3()  # Opens first found U3 over USB
    #d = u6.U6()  # Opens first found U6 over USB
    #d = ue9.UE9()  # Opens first found UE9 over USB
    # Opens a UE9 at IP Address 192.168.1.129
    #d = ue9.UE9(ethernet=True, ipAddress="192.168.1.129")

    isU3 = False
    if isinstance(d, u3.U3):
        isU3 = True

    if isU3:
        print("Setting FIO0-3 to analog, and the rest to digital.\n")
        d.writeRegister(50590, 15)

    # Reading Analog Inputs.
    print("Analog Inputs:")
    for i in range(4):
        register = 0 + i*2  # Starting register 0, 2 registers at a time
        print("AIN%s (register %s): %s volts" % (i, register, d.readRegister(register)))

    # Reading Digital I/O
    print("\nDigital I/O:\n")
    for i in range(4):
        dirRegister = 6100 + i  # Starting register 6100, 1 register at a time
        stateRegister = 6000 + i  # Starting register 6000, 1 register at a time
        fio = i
        if isU3:
            fio = i+4
            dirRegister = 6100 + 4 + i
            stateRegister = 6000 + 4 + i

        print("FIO%s (register %s) Direction: %s" % (fio, dirRegister, d.readRegister(dirRegister)))

        state = d.readRegister(stateRegister)
        print("FIO%s (register %s) State: %s" % (fio, stateRegister, state))

        if state == 0:
            state = 1
            wordState = "high"
        else:
            state = 0
            wordState = "low"

        print("Setting FIO%s to output %s (register %s = %s)." % (fio, wordState, stateRegister, state))
        d.writeRegister(stateRegister, state)

        print("FIO%s (register %s) Direction: %s" % (fio, dirRegister, d.readRegister(dirRegister)))
        print("FIO%s (register %s) State: %s\n" % (fio, stateRegister, d.readRegister(stateRegister)))

    # Seed the random number generator. Has nothing to do with Modbus.
    random.seed()

    # Reading and writing to a DAC
    print("Reading and writing to DACs:\n")
    for i in range(2):
        dacRegister = 5000 + i*2  # Starting register 5000, 2 registers at a time
        print("DAC%s (register %s) reads %s volts." % (i, dacRegister, d.readRegister(dacRegister)))

        voltage = float("%s.%s" % (random.randint(0, 4), random.randint(0, 9)))
        print("Setting DAC%s to %s volts." % (i, voltage))
        d.writeRegister(dacRegister, voltage)
        print("DAC%s (register %s) reads %s volts.\n" % (i, dacRegister, d.readRegister(dacRegister)))
