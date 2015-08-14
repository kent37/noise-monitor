# Sound/Noise logger - networked
# 2015, Rene Vega
# 2015-08-08, Fix registration logic.
# 2015-08-09, Add try/except on http request to catch connection errors
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

# server connection
URL = 'https://skyote.com/nl/nl-serverj.php'
PK  = '569gksxi4e7883,r60etgv-10d'
RefID = ''

# Raspbian linux has somewhat broken SSL that is going to be fixed soon,
# so in the meantime, disable the warning messages
logging.captureWarnings(True)

# The requests package will maintain keep-alive connections for a session,
# vastly speeds up HTTP accesses.
S = requests.Session()

def main():
   global URL
   global PK
   global RefID
   global Backup
   global TimeZone

   # Check for -bkup parameter
   if len(sys.argv) > 1 and sys.argv[1] == '-bkup':
      Backup = True
      print 'Creating backup log files'
   else: Backup = False

   # Create the bkup directory
   dir = 'bkup'
   if not os.path.exists(dir):
      os.makedirs(dir)

   # Query the server's time (diagnostic)
   query_args = { 'Action':'get-time', 'PassKey':PK }
   while True:
      try:
         response = S.post(URL, data=json.dumps(query_args))
         print response.content
         break                                                                                                                                                                                                                                  
      except KeyboardInterrupt:
         print '\nQuitting'
         exit
      except:
         print 'Request timeout'
         time.sleep(10)
         exit

   # Get the timezone difference
   TimeZone = GetTimeZone()
   print 'Timezone diff=', TimeZone

   # Register using the serial number of the RPI
   # This needs to be done at least once to create a device entry
   serial = GetSerial()
   query_args = { 'Action':'register', 'Serial':serial, 'PassKey':PK }
   response = S.post(URL, data=json.dumps(query_args))
   print response.content

   # Log in using the Raspberry PI's serial number. A reference ID is returned
   query_args = { 'Action':'data-login', 'Serial':serial, 'PassKey':PK }
   response = S.post(URL, data=json.dumps(query_args))
   if response.status_code != 200:
      print 'Server rejected login, code=', response.status_code
      sys.exit(1)
   jresp = json.loads(response.content)
   if jresp['Status'] == 'OK': RefID = jresp['Ref_ID']
   else: RefID = ''
   print 'Ref_ID=', RefID, ' ',response

   print 'Network logger started'

   foff = 0
   lastlog = ''
   delay = 10
   while True:
      # Send the log files to the server. Delete them when the
      # entire contents have been sent.
      while True:
         logf = GetLogFiles()
         if logf is None: break

         nlogs = len(logf)
         # if this is an archived log (not the active one), start
         # from the beginning of the file
         if len(logf) != 1: foff = 0;
         if lastlog != logf[0]:
            print 'Processing log file (of ', nlogs, '): ', logf[0], ' @=', foff
            lastlog = logf[0]
         foff = ProcessLogFile(logf[0], foff)

         # positive offset means the file was completely processed.
         # Usually that means the log file should be deleted or backed up,
         # but when only one file is present, it is the active one and needs
         # to be left intact.
         if (foff > 0):
            if nlogs != 1:
               if Backup: os.rename('logs/' + logf[0], 'bkup/' + logf[0])
               else:      os.remove('logs/' + logf[0])
               foff = 0
            else:
               print 'real-time', datetime.datetime.now()
               time.sleep(delay)

         # A negative offset means the file was not completely processed.
         # This usually indicates a network connection problem, so set up
         # for a retry.
         else:
            foff = -foff
            print 'lost coms, retrying', datetime.datetime.now()
            break

      time.sleep(10)

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
   logf = os.listdir('logs')
   logf.sort()
   return logf

def ProcessLogFile(logf, foff):
   global TimeZone

   # Send each item of the file to the server.
   # If the server times out, indicate failure
   ofoff = foff
   maxts = ''

   f = open('logs/' + logf, 'r')
   if f is None: return None;
   if foff != 0: f.seek(foff)

   cnt = 0
   for line in f:
      foff = f.tell()
      items = line.split(',')
      # if foff != 0: print 'offset=', foff, 'line=', line

      if len(items) > 2:
         if (maxts == '') | (items[0] > maxts):
            # timestemp, meter_model, weight, rate, mode, range, num_samp, db1, db2, ...
            # 2015-08-01 14:12:34.440317,WENSN 1361,A,fast,samp,30-80db,2,32.8,35.2
            query_args = { 'Action':'log', 'PassKey':PK, 'Ref_ID':RefID,
                           'Timestamp':items[0], 'Meter':items[1],
                           'Weighting':items[2],'TimeZone':TimeZone, 'Samples':items[6],
                           'Data':",".join([str(item) for item in items[7:]]) }
            try:
               response = S.post(URL, data=json.dumps(query_args))
               if response.status_code != 200:
                  f.close()
                  return -foff;
            except:
               f.close()
               return -foff;

            # if the server tells us this was a duplicate record, get the maximum timestamp
            # then use it to skim through the file. This avoids swamping
            # the server with wasteful transactions.
            jresp = json.loads(response.content)
            if jresp['Status'] == 'Duplicate':
               maxts = jresp['Timestamp']
               print 'Duplicate, skipping to', maxts

      else: print 'Tossing ', foff, ':', line

      cnt += 1
      if (cnt %  100) == 0: print 'Processed: ', cnt

   f.close()
   return foff;

main()
