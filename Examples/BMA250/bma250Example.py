"""
Name: bma250Example
Desc: An example showing how to use the bma250 module with the U6.
Reads data as fast as possible.

This BMA250 example source code is licensed under MIT X11.

   Copyright (c) 2013 Aura Labs, Inc.  http://oneaura.com/

   Permission is hereby granted, free of charge, to any person obtaining a copy
   of this software and associated documentation files (the "Software"), to deal
   in the Software without restriction, including without limitation the rights
   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
   copies of the Software, and to permit persons to whom the Software is
   furnished to do so, subject to the following conditions:

   The above copyright notice and this permission notice shall be included in
   all copies or substantial portions of the Software.

   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
   THE SOFTWARE.

"""

import bma250
import u6

device = u6.U6()
bma = bma250.BMA250(device, autoUpdate=False)

while True:
	bma.update()
	xaccel = bma.getXAccel()
	yaccel = bma.getYAccel()
	zaccel = bma.getZAccel()
	temp = bma.getTemperature()

	print "xaccel: %4d, yaccel: %4d, zaccel: %4d, temp: %4d" % \
	    (xaccel, yaccel, zaccel, temp)

