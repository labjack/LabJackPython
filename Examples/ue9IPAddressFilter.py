"""
Demonstrates how to use the IP Address Filter UE9 function
(UE9.ipAddressFilter) to filter the IP addresses that can connect to a UE9
over TCP. Requires UE9 Comm. firmware 1.56 or newer.

Note: Our Python interfaces throw exceptions when there are any issues with
device communications that need addressed. Many of our examples will
terminate immediately when an exception is thrown. The onus is on the API
user to address the cause of any exceptions thrown, and add exception
handling when appropriate. We create our own exception classes that are
derived from the built-in Python Exception class and can be caught as such.
For more information, see the implementation in our source code and the
Python standard documentation.
"""
import ue9


d = ue9.UE9()  # Open first found UE9 over USB

commFW = d.commConfig()["CommFWVersion"]
if float(commFW) < 1.56:
    print("Your UE9 has Comm firmware %s. The IP Address Filter function " +
          "requires Comm firmware 1.56 or newer." % commFW)
    print("Please upgrade your Comm firmware.")
    d.close()
    exit()

print("IP Address Filter demonstration:")

# Uncomment the below code to turn on IP filtering and set the IP addresses to
# filter.
'''
print("  Setting IPs to filter")
# Set the 5 IP filters here
ip0 = "192.168.1.10"
ip1 = "192.168.1.11"
ip2 = "192.168.1.12"
ip3 = "192.168.1.13"
ip4 = "192.168.1.14"
ips = d.ipAddressFilter(1, ip0, ip1, ip2, ip3, ip4)
'''

# Uncomment the below code to turn off IP filtering
'''
print("  Turn off IP filtering")
ips = d.ipAddressFilter(1, "255.255.255.255")
'''

print("  Current IPs set:")
ips = d.ipAddressFilter()
for i in range(5):
    print("    IP%i: %s" % (i, ips['IP%i' % i]))

d.close()
