#!/usr/bin/env python

# u3SampleAndLogToCloudDot.py
#
# This program demonstrates how to sample data from a USB LabJack and 
# log it to CloudDot using CloudDot's REST API.
# 
# Requirements:
# 
# 1. A U3 (You can modify the code to use another LabJack.)
# 2. A UNIX-compatible computer (Replace the signal.SIGALRM usage with sleep() on another platform)
# 3. The httplib2 Python module. Install it via
#     $ sudo easy_install httplib2
#    or download it from
#     http://code.google.com/p/httplib2/
# 4. A CloudDot account. Start with the walkthrough and tutorial if you don't have one yet:
#     http://labjack.com/support/clouddot/users-guide/1
# 5. Details from your CloudDot account:
#     a. Username
#     b. API Key (on your Account page)
#     c. A channel nickname from a virtual channel (make a virtual channel on your Channels page)
#
# For information on the CloudDot REST API, visit: 
#     http://labjack.com/support/clouddot/rest-api

# Replace these three fields
CLOUDDOT_USERNAME = ""
CLOUDDOT_API_KEY  = "01234567890123456789"
CLOUDDOT_CHANNEL  = "Temperature"

SAMPLE_INTERVAL   = 30 # Sample and post to CloudDot after this time in seconds
MODBUS_REGISTER   = 0  # Read from this register to get the data. See http://labjack.com/support/modbus

import u3
import signal
from datetime import datetime

from httplib2 import Http
from urllib import urlencode

def sampleAndPost(*args):
    print "----- Gathering sample at", datetime.now()
    reading = d.readRegister(MODBUS_REGISTER)
    print "===== Read", reading
    data = dict(value = reading)
    # Here is the call that posts to CloudDot
    resp, content = h.request(writeUrl, "POST", urlencode(data))
    print "+++++ Post to CloudDot at", datetime.now(), "Response status:", resp["status"]
    if resp["status"].startswith('2') == False:
        raise Exception("Post failed; check your CloudDot username, API key, and channel. Response status was: %s" % (resp["status"],))
    print

d = u3.U3()
writeUrl = "http://cloudapi.labjack.com/%s/channels/%s/write.json" % (CLOUDDOT_USERNAME, CLOUDDOT_CHANNEL)
h = Http()
h.add_credentials(CLOUDDOT_USERNAME, CLOUDDOT_API_KEY)

# Call it once at first because we're impatient
sampleAndPost()

# Set it up to call every SAMPLE_INTERVAL
signal.signal(signal.SIGALRM, sampleAndPost)
signal.setitimer(signal.ITIMER_REAL, SAMPLE_INTERVAL, SAMPLE_INTERVAL)
while True:
    signal.pause()

