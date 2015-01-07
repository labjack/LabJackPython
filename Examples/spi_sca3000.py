"""
Demonstrates SPI protocol usage with a SCA3000 3-axis accelerometer. For full
details on the example refer to the "SCA3000 3-axis accelerometer-SPI"
AppNote online:

  http://labjack.com/support/app-notes/sca3000-3-axis-accelerometer-spi

The default SPI settings for a UE9 are:

  AutoCS = True, DisableDirConfig = False, SPIMode = 'A', SPIClockFactor = 0,
  CSPINNum = 1 (FIO1), CLKPinNum = 0 (FIO0), MISOPinNum = 3 (FIO3),
  MOSIPinNum = 2 (FIO2)

The default SPI settings for a U6 are:

  AutoCS = True, DisableDirConfig = False, SPIMode = 'A', SPIClockFactor = 0,
  CSPINNum = 0 (FIO0), CLKPinNum = 1 (FIO1), MISOPinNum = 2 (FIO2),
  MOSIPinNum = 3 (FIO3)

The default SPI settings for a U3 are:

  AutoCS = True, DisableDirConfig = False, SPIMode = 'A', SPIClockFactor = 0,
  CSPINNum = 4 (FIO4), CLKPinNum = 5 (FIO5), MISOPinNum = 6 (FIO6),
  MOSIPinNum = 7 (FIO7)

Note the CSPINNum, CLKPinNum, MISOPinNum, and MOSIPinNum pin numbers and make
your connections accordingly.
"""
import os
import time

#By default the example uses a UE9. Uncomment the U6 or U3 section if that is
#your device and then comment out the UE9 section.

import ue9
d = ue9.UE9() #Open first found UE9 over USB

'''
import u6
d = u6.U6() #Open first found U6 over USB
'''

'''
import u3
d = u3.U3() #Open first found U3 over USB
d.configIO(FIOAnalog = 0x0F) #For this example FIO4-7 need to be digital IO
'''

#convert takes in the 11-bit response and converts it into an integer
def convert(byte1, byte2):
    ans = 0
    i = 128
    j = 128
    while i > 0:
        if(byte1 > i):
            ans = ans << 1
            ans = ans + 1
            byte1 = byte1 - i  
        else:
            ans = ans << 1
        i = i >> 1
    while j > 0:
        if(byte2 > j):
            ans = ans << 1
            ans = ans + 1
            byte2 = byte2 - i
        else:
            ans = ans << 1
        j = j >> 1
    return ans

#converts the resulting integer into a factor of G.... I'm not sure if this
#conversion is correct, but it results in a sensible answer, look at the
#datasheet for understanding the binary results.
def normalize(value):
    ans = 0
    if(value > 20000):
        ans = convert(255, 255) - value
        return (-ans)*1.0 / 10000
    else:
        return value*1.0 / 10000

#
# Reading spontaneous x, y, and z acceleration measurements
#

#Press ctrl-C to exit the program
while(True):
    results = d.spi([0x4<<2, 0])  #gets information from LSBx register
    LSBx = results['SPIBytes'][1]
    results = d.spi([0x5<<2, 0])  #gets information from MSBx register
    MSBx = results['SPIBytes'][1]
    results = d.spi([0x6<<2, 0])  #gets information from LSBy register
    LSBy = results['SPIBytes'][1]
    results = d.spi([0x7<<2, 0])  #gets information from MSBy register
    MSBy = results['SPIBytes'][1]
    results = d.spi([0x8<<2, 0])  #gets information from LSBz register
    LSBz = results['SPIBytes'][1]
    results = d.spi([0x9<<2, 0])  #gets information from MSBz register
    MSBz = results['SPIBytes'][1]
    os.system("clear")
    print "x: " + str(normalize(convert(MSBx, LSBx))) + "g" 
    print "y: " + str(normalize(convert(MSBy, LSBy))) + "g"
    print "z: " + str(normalize(convert(MSBz, LSBz))) + "g"
    time.sleep(.01)
    
#Uncomment out the below code for the ring buffer mode demonstration.
#
# Ring Buffer Mode
#
'''
try:
    d.spi([((0x14<<1)+1)<<1, 0xC0]) #This sets up the sensor into 8-bit ring buffer mode

    #Press ctrl-C to exit the program
    while(True):
        n = d.spi([0x15<<2, 0x0]) #this reads how many results are available in the buffer
        getResults = [0]*n['SPIBytes'][1] #create an array getResults that is filled with n 0's which happens to be (#results in buffer)*3+1
        getResults[0] = 0xF << 2  #edit the first number in the array to prepare the array to be sent over SPI and get the results
        print d.spi(getResults)   #print out the results array, the first is a bogus variable, but after its x,y,z,x,y,z.....
        time.sleep(.001)
        os.system("clear")        #this function only works on mac and maybe linux, probably not for windows... It clears the command line to make the results easier to read/understand
except KeyboardInterrupt:         #this allows the program to quit when you press "ctrl C", it takes the sensor out of ring buffer mode and turns off the interrupt.  
    print " ctrl C received, shutting down program"
    d.spi([((0x14<<1)+1)<<1, 0x0]) #take sensor out of ring buffer mode
    d.spi([0x16<<2, 0])            #re-set interrupt
    d.close()                      #close the device
'''
