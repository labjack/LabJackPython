"""
Demonstrates reading analog inputs from a U6 using the getAIN and getFeedback
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
import u6


# Open first found U6.
# To open a specific U6, set firstFound to False and set the localId or
# serial number of the U6.
dev = u6.U6(firstFound=True, localId=None, serial=None)

# Get the calibration constants from the U6, otherwise default nominal values
# will be be used for binary to decimal (analog) conversions.
dev.getCalibrationData()

# Common analog input settings.
resolution_index = 0  # Resolution Index = 0 (default)
gain_index = 0  # Gain Index = 0 (x1 which is +/-10V range)
settling_factor = 0  # Settling Factor = 0 (auto)

# Get a single-ended reading from AIN0 using the getAIN convenience method.
# getAIN will get the binary voltage and convert it to a decimal value.
ain0 = dev.getAIN(positiveChannel=0,
                  resolutionIndex=resolution_index,
                  gainIndex=gain_index,
                  settlingFactor=settling_factor,
                  differential=False)
print("AIN0 = %.3f V" % ain0)

# Get a single-ended reading from AIN0 using the getFeedback function with
# IOType AIN24.
# getFeedback gets the binary voltage only.
commands = u6.AIN24(PositiveChannel=0,
                    ResolutionIndex=resolution_index,
                    GainIndex=gain_index,
                    SettlingFactor=settling_factor,
                    Differential=False)
results = dev.getFeedback(commands)
# Convert binary voltage to a decimal value.
ain0 = dev.binaryToCalibratedAnalogVoltage(gainIndex=gain_index,
                                           bytesVoltage=results[0],
                                           is16Bits=False,
                                           resolutionIndex=resolution_index)
print("AIN0 = %.3f V" % ain0)

# Get a single-ended reading from AIN0 and a differential reading from
# AIN2-AIN3 using the getFeedback function with IOType AIN24.
# getFeedback gets the binary voltage only.
commands = [0]*2
commands[0] = u6.AIN24(PositiveChannel=0,
                       ResolutionIndex=resolution_index,
                       GainIndex=gain_index,
                       SettlingFactor=settling_factor,
                       Differential=False)
commands[1] = u6.AIN24(PositiveChannel=2,
                       ResolutionIndex=resolution_index,
                       GainIndex=gain_index,
                       SettlingFactor=settling_factor,
                       Differential=True)
results = dev.getFeedback(commands)
# Convert binary voltages to decimal values.
ain0 = dev.binaryToCalibratedAnalogVoltage(gainIndex=gain_index,
                                           bytesVoltage=results[0],
                                           is16Bits=False,
                                           resolutionIndex=resolution_index)
ain2_3 = dev.binaryToCalibratedAnalogVoltage(gainIndex=gain_index,
                                             bytesVoltage=results[1],
                                             is16Bits=False,
                                             resolutionIndex=resolution_index)
print("AIN0 = %.3f V, AIN2-AIN3 = %.3f V" % (ain0, ain2_3))

# Close the U6.
dev.close()
