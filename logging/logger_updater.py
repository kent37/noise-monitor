# Sound/Noise logger - updater
# 2015-10-02, Rene Vega
#
# This applet is the auto updater for the noise monitor system.
# It is invoked by the logger_network applet whenever it receives
# an update response.
#

import time
import logging
import json
import ssl
import requests
import os
import datetime
import sys
import syslog
import subprocess

Version = '1.0'
Path = os.path.dirname(os.path.realpath(sys.argv[0]))+ '/'

# server connection
URL = 'https://skyote.com/nl/nl-serverj.php'
PK  = '569gksxi4e7883,r60etgv-10d'
RefID = ''

# Raspbian linux has a somewhat broken SSL that is going to be fixed soon,
# so in the meantime, disable the warning messages
logging.captureWarnings(True)

# The requests package will maintain keep-alive connections for a session,
# vastly speeds up HTTP accesses.
S = requests.Session()

def main():
    global Version
    global Path
    global S
    global URL
    global PK
    global RefID
    global Backup
    global TimeZone

    # Check for the action parameter
    if len(sys.argv) > 1:
        print os.path.dirname(os.path.realpath(sys.argv[0]))
        Log('Updater version: ' + Version + 'Command: ' + sys.argv[1])
    else:
        sys.exit(0)

    jresp = json.loads(sys.argv[1])
    action = jresp['Action']
    
    if action == 'reboot':
        ipa = subprocess.check_output(['sudo','reboot'], stderr=subprocess.STDOUT)
        sys.exit(0)
    elif action == 'toggle-wlan0':
        ipa = subprocess.check_output(['sudo','ifdown','wlan0'], stderr=subprocess.STDOUT)
        ipa = subprocess.check_output(['sudo','ipup','wlan0'], stderr=subprocess.STDOUT)
    elif action == 'clear-bkup':
        ipa = subprocess.check_output(['sudo','rm', Path + '/bkup/*'], stderr=subprocess.STDOUT)
    elif action == 'run':
		try:
			fname = jpresp['Fname']
			ipa = subprocess.check_output([fname], stderr=subprocess.STDOUT)
		except: pass
    elif action == 'write-file':
		try:
			fname = jresp['Fname']
			content = jresp['content']
			f = open(fname, 'w')
			f.write(content);
			f.close()
		except: pass
    elif action == 'say':
		try:
			Log(jresp['Text']);
		except: pass
        
    #query_args = { 'Action':'get-time', 'PassKey':PK }
    # response = S.post(URL, data=json.dumps(query_args))
    return

# Get the timezone
def GetTimeZone():
   loc = time.localtime()
   gmt = time.gmtime()
   return -time.timezone / 3600

# Get the serial number of the Raspberry PI
def GetSerial():
   serial = ''
   f = open('/proc/cpuinfo', 'r')
   for l in f:
      if l[0:6] == 'Serial': serial = l[10:26]
   f.close()
   return serial

# Get the sorted list of log file name
def GetLogFiles():
   global Path
   logf = os.listdir(Path + 'logs')
   logf.sort()
   return logf

def Log(msg):
   print msg
   syslog.syslog(msg)

def GetCoreTemp():
   temp = os.popen('vcgencmd measure_temp').readline()
   temp = temp.replace('temp=', '').replace("'C\n","")
   return temp

def GetCoreVolts():
   volts = os.popen('vcgencmd measure_volts').readline()
   volts = volts.replace('volt=', '').replace('V\n', '')
   return volts

def containsOnly(str, set):
    # Check whether 'str' contains only the chars in 'set'
    for c in str:
       if c not in set: return 0
    return 1

main()
