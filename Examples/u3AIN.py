"""
Demonstrates reading analog inputs from a U3 using the getAIN and getFeedback
methods.

Note: Our Python interfaces throw exceptions when there are any issues with
device communications that need addressed. Many of our examples will
terminate immediately when an exception is thrown. The onus is on the API
user to address the cause of any exceptions thrown, and add exception
handling when appropriate. We create our own exception classes that are
derived from the built-in Python Exception class and can be caught as such.
For more information, see the implementation in our source code and the
Python standard documentation.
"""
import u3


# Open first found U3.
# To open a specific U3, set firstFound to False and set the localId or
# serial number of the U3.
dev = u3.U3(firstFound=True, localId=None, serial=None)

# Get the calibration constants from the U3, otherwise default nominal values
# will be be used for binary to decimal (analog) conversions.
dev.getCalibrationData()

# Common analog input settings.
long_settling = True  # Long Settling = True
quick_sample = False  # Quick Sample = False
# If we are using a U3-HV and AIN0-AIN3, during calibration conversion we want
# to set isLowVoltage to False. Otherwise, all U3-LV analog inputs and all
# U3-HV analog inputs after AIN3 are low-voltage, so set isLowVoltage to True.
is_low_voltage_ain0_to_ain3 = dev.isHV != True

# Configure all FIO0-FIO7 to analog inputs (255 = b11111111).
dev.configIO(FIOAnalog=255)

# Get a single-ended reading from AIN0 using the getAIN convenience method.
# getAIN will get the binary voltage and convert it to a decimal value.
ain0 = dev.getAIN(posChannel=0,
                  negChannel=31,
                  longSettle=long_settling,
                  quickSample=quick_sample)
print("AIN0 = %.3f V" % ain0)

# Get a single-ended reading from AIN0 using the getFeedback function with
# IOType AIN.
# getFeedback gets the binary voltage only.
commands = u3.AIN(PositiveChannel=0,
                  NegativeChannel=31,
                  LongSettling=long_settling,
                  QuickSample=quick_sample)
results = dev.getFeedback(commands)
# Convert binary voltage to a decimal value.
ain0 = dev.binaryToCalibratedAnalogVoltage(bits=results[0],
                                           isLowVoltage=is_low_voltage_ain0_to_ain3,
                                           isSingleEnded=True,
                                           isSpecialSetting=False,
                                           channelNumber=0)
print("AIN0 = %.3f V" % ain0)

# Get a single-ended reading from AIN0 and a differential reading from
# AIN4-AIN5 using the getFeedback function with IOType AIN.
# getFeedback gets the binary voltage only.
commands = [0]*2
commands[0] = u3.AIN(PositiveChannel=0,
                     NegativeChannel=31,
                     LongSettling=long_settling,
                     QuickSample=quick_sample)
commands[1] = u3.AIN(PositiveChannel=4,
                     NegativeChannel=5,
                     LongSettling=long_settling,
                     QuickSample=quick_sample)
results = dev.getFeedback(commands)
# Convert binary voltages to decimal values.
ain0 = dev.binaryToCalibratedAnalogVoltage(bits=results[0],
                                           isLowVoltage=is_low_voltage_ain0_to_ain3,
                                           isSingleEnded=True,
                                           isSpecialSetting=False,
                                           channelNumber=0)
ain4_5 = dev.binaryToCalibratedAnalogVoltage(bits=results[1],
                                             isLowVoltage=True,
                                             isSingleEnded=False,
                                             isSpecialSetting=False,
                                             channelNumber=4)
print("AIN0 = %.3f V, AIN4-AIN5 = %.3f V" % (ain0, ain4_5))

# Close the U3.
dev.close()
