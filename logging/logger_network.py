# Sound/Noise logger - networked
# 2015, Rene Vega
# 2015-08-08, Fix registration logic.
# 2015-08-09, Add try/except on http request to catch connection errors
# 2015-09-11, Fix handling timeout exceptions (sometimes the server goes offline)
# 2015-09-20, Fix race condition between meter log writing to the log file and the network logger reading from it.
# 2015-09-21, Add core temperature/voltage logging.
# 2015-09-22, Add version control
# 2015-09-23, Add batched samples to speed up catchup mode and to lower the physical write rate.
# 2015-09-23, 2.1 - Fix another race condition.
# 2015-09-24, 2.2 - Clean up error messages.
# 2015-09-24, 2.3 - Skip incomplete data altogether
# 2015-09-24, 2.4 - Serious corruption issue (power off?) Skip incomplete data altogether.
# 2015-10-02, 2.5 - Suspect a sessions bug, closing a session after an post exception fails.
# 2015-10-02, 2.6 - Add update and reboot response transfer logic.
# 2015-11-01, 2.7 - Include the network version, and WIFI  signal strength
# 2015-11-19, 2.8 - Reduce the buffering of the log fiels to a single line.
#
# This applet processes all the log files found in the logs directory.
# It sends the data to the common server for safekeeping and analysis.
# It can be restarted at any time. Old files are sent in bulk. The
# active log file is sent up to its end and then a real-time poll
# occurs to grab any new data dumped into the log file by the logger
# applet. If further local processing of the data is desired, start
# this applet with the -bkup parameter:
# sudo python logger_network.py -bkup
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

Version = '2.8'
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
print os.path.dirname(os.path.realpath(sys.argv[0]))

def main():
   global Version
   global Path
   global S
   global URL
   global PK
   global RefID
   global Backup
   global TimeZone

   Log('Network logger started, version: ' + Version)

   # Check for -bkup parameter
   if len(sys.argv) > 1 and sys.argv[1] == '-bkup':
      Backup = True
      Log('Network logger will create backup log files')
   else: Backup = False

   # Create the bkup directory
   dir = Path + 'bkup'
   if not os.path.exists(dir):
      os.makedirs(dir)

   # Query the server's time (diagnostic)
   query_args = { 'Action':'get-time', 'PassKey':PK }
   while True:
      try:
         response = S.post(URL, data=json.dumps(query_args))
         Log(response.content)
         break
      except KeyboardInterrupt:
         print '\nQuitting'
         sys.exit(1)
      except:
         print 'Request timeout'
         time.sleep(10)

   # Get the timezone difference
   TimeZone = GetTimeZone()
   Log('Timezone diff=' + str(TimeZone))

   # Register using the serial number of the RPI
   # This needs to be done at least once to create a device entry
   serial = GetSerial()
   query_args = { 'Action':'register', 'Serial':serial, 'PassKey':PK }
   response = S.post(URL, data=json.dumps(query_args))
   Log(response.content)

   while True:
        # Log in using the Raspberry PI's serial number. A reference ID is returned
        query_args = { 'Action':'data-login', 'Serial':serial, 'PassKey':PK }
        response = S.post(URL, data=json.dumps(query_args))
        if response.status_code != 200:
            Log('Server rejected login, code=' + str(response.status_code))
            time.sleep(10)
            continue
        jresp = json.loads(response.content)
        if jresp['Status'] == 'OK':
            RefID = jresp['Ref_ID']
            Log('Ref_ID=' + RefID + ' ' + str(response))
            break
        else:
            Log('Login rejected: ' + jresp['Status'])
            time.sleep(10)

   Log('Network logger processing files')

   foff = 0
   lastlog = ''
   delay = 10
   while True:
      # Send the log files to the server. Delete them when the
      # entire contents have been sent.
      while True:
         logf = GetLogFiles()
         nlogs = len(logf)
         if nlogs == 0: break

         # if this is an archived log (not the active one), start
         # from the beginning of the file
         if nlogs > 1: foff = 0;
         if lastlog != logf[0]:
            Log('Processing log file ' + logf[0] + ' @=' + str(foff) + ', ' + str(nlogs) + ' to go.')
            lastlog = logf[0]

         foff = ProcessLogFile(logf[0], foff)

         # zero or positive offset means the file was completely processed.
         # Usually that means the log file should be deleted or backed up,
         # but when only one file is present, it is the active one and needs
         # to be left intact.
         if (foff >= 0):
            if nlogs > 1:
               if Backup: os.rename(Path + 'logs/' + logf[0], Path + 'bkup/' + logf[0])
               else:      os.remove(Path + 'logs/' + logf[0])
               foff = 0
               Log('Processed log file: ' + logf[0])
            else:
               print 'real-time', datetime.datetime.now()
               time.sleep(delay)

         # A negative offset means the file was not completely processed.
         # This usually indicates a network connection problem, so set up
         # for a retry.
         else:
            foff = -foff
            Log('Retrying log file processsing');
            break

      # Check for server actions
      CheckServerActions()
      time.sleep(10)

# Check server for actions
def CheckServerActions():
    global Version
    global Path
    global S
    global URL
    global PK
    global RefID

    query_args = { 'Action':'Check', 'PassKey':PK, 'Ref_ID':RefID }
    try:
        response = S.post(URL, data=json.dumps(query_args))
    except KeyboardInterrupt:
        print '\nQuitting'
        sys.exit(1)
    except Exception, e:
        Log('HTTP Request exception: ' + str(e))
        S = requests.Session()
        return

    if response.status_code == 200:
        jresp = json.loads(response.content)
        DoServerAction(jresp);

def DoServerAction(jresp):
    global Path

    jstat = jresp['Status']
    action = jresp['Action'] # a json string

    # Special command to reboot the system.
    if jstat == 'Reboot':
        Log('Server requests reboot');
        time.sleep(1)
        ipa = subprocess.check_output(['sudo','reboot'], stderr=subprocess.STDOUT)
        sys.exit(1)
    elif jstat == 'More':
        Log('Server requests more action: ' + action)
        updater = Path + 'logger_updater.py'
        if os.path.isfile(updater):
            try: subprocess.call(['python',updater, action])
            except: pass
    elif jstat != 'OK':
        Log('Server error status: ' + jstat);

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

def ProcessLogFile(logf, foff):
   print 'ProcessLogFile'
   global TimeZone
   global S
   global Path

   # Send each item of the file to the server.
   # If the server times out, indicate failure
   ofoff = foff
   maxts = ''

   f = open(Path + 'logs/' + logf, 'r', 1) # line buffered
   if f is None: return None;
   if foff != 0: f.seek(foff)

   cnt = 0
   for line in f:
      nfoff = f.tell()
      items = line.split(',')

      try:
         # Hack: If a partial line was read, skip over it (seeing nulls).
         if len(items) < 8 or len(items) < (8 + int(items[7])):
            Log( 'Incomplete line, found, ' + str(len(items)) + ' items @' + str(foff) +" skip to: @" + (str(nfoff)))
            continue;

         # pre v2 compatibility hack
         if not containsOnly(items[1], "0123456789."):
            items.insert(1,'1.0');

         if (maxts == '') | (items[0] > maxts):
            # timestemp, version, meter_model, weight, rate, mode, range, num_samp, db1, db2, ...
            # 2015-08-01 14:12:34.440317,2.0,WENSN 1361,A,fast,samp,30-80db,2,32.8,35.2
            query_args = { 'Action':'log', 'PassKey':PK, 'Ref_ID':RefID,
                           'Timestamp':items[0], 'NetVersion':Version, 'Version':items[1], 'Meter':items[2],
                           'Weighting':items[3],'TimeZone':TimeZone, 'Samples':items[7],
                           'Mode':items[5], 'WifiDB':GetWifiDB(),
                           'Data':",".join([str(item) for item in items[8:]]),
                           'Temp':GetCoreTemp(), 'Volts':GetCoreVolts() }
            # print query_args
            try:
               response = S.post(URL, data=json.dumps(query_args))
               # Anything other than a 200 status is a deep error condition. Close sessions then
               # return, that will drive the logic to delay for several seconds and retry.
               if response.status_code != 200:
                  Log('HTTP Request status error: ' + str(response.status.code))
                  f.close()
                  S.close()
                  S = requests.Session()
                  return -foff;
            except KeyboardInterrupt:
               print '\nQuitting'
               sys.exit(1)
            except Exception, e:
               Log('HTTP Request exception: ' + str(e))
               f.close()
               # S.close()
               S = requests.Session()
               return -foff

            # if the server tells us this was a duplicate record, get the maximum timestamp
            # then use it to skim through the file. This avoids swamping
            # the server with wasteful transactions.
            jresp = json.loads(response.content)
            jstat = jresp['Status'];
            if jstat == 'Duplicate':
               maxts = jresp['Timestamp']
               Log('Server says duplicate, skipping to ' + str(maxts))
            # Special command for more action.
            elif jstat == 'Reboot' or jstat == 'More':
                DoServerAction(jresp)
            elif jstat != 'OK':
               Log('Server error status: ' + jstat);
               f.close()
               return -foff

      except Exception, e:
         Log( 'Tossing incomplete line ' + str(foff) + ':' + str(e))
         # close the file and retry
         f.close()
         return -foff;

      foff = nfoff;
      cnt += 1
      if (cnt %  100) == 0: Log('Processed: ' + str(cnt))

   f.close()
   return foff

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

def GetWifiDB():
   wdb = os.popen('cat /proc/net/wireless | grep wlan').readline()
   wdb += '-127 -127 -127 -127'
   wdbl = wdb.split()
   wdb = wdbl[3];
   return wdb

def containsOnly(str, set):
    # Check whether 'str' contains only the chars in 'set'
    for c in str:
       if c not in set: return 0
    return 1

main()
