"""
" An example program to show you how easy it is to work with Modbus on a
" LabJack.
"
" Be sure to check out the Modbus map (http://labjack.com/support/modbus) for a
" full list of registers.
"""

import u3, u6, ue9
import random

if __name__ == '__main__':
    print "This program shows how to work with modbus and your device. Registers are taken directly from the Modbus map (http://labjack.com/support/modbus).\n"
    
    print "Opening device...",
    d = u3.U3() # Opens first found U3 over USB
    #d = u6.U6() # Opens first found U6 over USB
    #d = ue9.UE9() # Opens first found UE9 over USB
    # Opens a UE9 at IP Address 192.168.1.129
    #d = ue9.UE9( ethernet = True, ipAddress = "192.168.1.129") 
    print "Done\n"

    isU3 = False
    if isinstance(d, u3.U3):
        isU3 = True
    
    if isU3:
        print "Setting FIO0-3 to analog, and the rest to digital...",
        d.writeRegister(50590, 15)
        print "Done\n"
        
    # Reading Analog Inputs.
    print "Analog Inputs:"
    for i in range(4):
        register = 0 + i*2 # Starting register 0, 2 registers at a time
        print "AIN%s (register %s): %s" % (i, register, d.readRegister(register))
        
    # Reading Digital I/O
    print "\nDigital I/O:"
    for i in range(4):
        dirRegister = 6100 + i # Starting register 6100, 1 register at a time
        stateRegister = 6000 + i # Starting register 6000, 1 register at a time
        fio = i
        if isU3:
            fio = i+4
            dirRegister = 6100 + 4 + i
            stateRegister = 6000 + 4 + i
        
        print "FIO%s (register %s) Direction: %s" % (fio, dirRegister, d.readRegister(dirRegister))
        
        state = d.readRegister(stateRegister)
        print "FIO%s (register %s) State: %s" % (fio, stateRegister, state)
        
        if state == 0:
            state = 1
            wordState = "high"
        else:
            state = 0
            wordState = "low"
        
        print "Setting FIO%s to output %s (register %s = %s )..." % (fio, wordState, stateRegister, state),
        d.writeRegister(stateRegister, state)
        print "Done"
        
        print "FIO%s (register %s) Direction: %s" % (fio, dirRegister, d.readRegister(dirRegister))
        print "FIO%s (register %s) State: %s\n" % (fio, stateRegister, d.readRegister(stateRegister))
    
    # Seed the random number generator. Has nothing to do with modbus
    random.seed()
    
    # Reading and writing to a DAC
    print "\nReading and writing to DACs:"
    for i in range(2):
        dacRegister = 5000 + i*2 # Starting register 5000, 2 registers at a time
        print "DAC%s (register %s) reads %s Volts." % (i, dacRegister, d.readRegister(dacRegister))
        
        voltage = float("%s.%s" % (random.randint(0,4), random.randint(0,9)) )
        print "Setting DAC%s to %s Volts..." % (i, voltage),
        d.writeRegister(dacRegister, voltage)
        print "Done"
        print "DAC%s (register %s) reads %s Volts.\n" % (i, dacRegister, d.readRegister(dacRegister))