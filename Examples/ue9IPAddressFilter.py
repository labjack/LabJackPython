"""
Demonstrates how to use the IP Address Filter UE9 function (UE9.ipAddressFilter)
to filter the IP addresses that can connect to a UE9 over TCP. Requires UE9
Comm. firmware 1.56 or newer.
"""

import ue9

d = ue9.UE9() #Open first found UE9 over USB

commFW = d.commConfig()["CommFWVersion"]
if float(commFW) < 1.56:
    print "Your UE9 has Comm firmware " + commFW + ". The IP Address Filter function requires Comm firmware 1.56 or newer."
    print "Please upgrade your Comm firmware."
    d.close()
    exit()

print "IP Address Filter demonstration:"

#Uncomment the below code to turn on IP filtering and set the IP addresses to
#filter.
'''
print "  Setting IPs to filter"
#Set the 5 IP filters here
ip0 = "192.168.1.10"
ip1 = "192.168.1.11"
ip2 = "192.168.1.12"
ip3 = "192.168.1.13"
ip4 = "192.168.1.14"
ips = d.ipAddressFilter(1, ip0, ip1, ip2, ip3, ip4)
'''

#Uncomment the below code to turn off IP filtering
'''
print "  Turn off IP filtering"
ips = d.ipAddressFilter(1, "255.255.255.255")
'''

print "  Current IPs set:"
ips = d.ipAddressFilter()
print "    IP0: " + ips['IP0'] + "\n" + "    IP1: " + ips['IP1'] + "\n" + \
      "    IP2: " + ips['IP2'] + "\n" + "    IP3: " + ips['IP3'] + "\n" + \
      "    IP4: " + ips['IP4']

d.close()

