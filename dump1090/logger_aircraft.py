# Logger for aircraft data from dump1090
# With help from Rene Vega

import csv
import datetime
import time
import sys
import os
import syslog

import parse_aircraft as pa

Version = '1.0'
Path = os.path.dirname(os.path.realpath(sys.argv[0])) + '/'

LogDuration = 7200

def Log(msg):
   print msg
   syslog.syslog(msg)

def main():
   global Version
   global Path

   Log('Aircraft logger started, version: ' + Version)

   # Create the Log directory if not found
   dir = Path + 'tracks/'
   if not os.path.exists(dir):
      os.makedirs(dir)

   while True:
      # Make the log name, then open it.
      dt = str(datetime.datetime.now()).replace(' ','_')
      logname = dir + 'Tracks_' + dt
      Log('Logging to: ' + logname)
      logfile = open(logname, 'a')

      # Gather the meter data, sampling twice a second.
      # Also decode the meter options
      try:
         if GetSamples(logfile) == False:
            Log('/nGlitch or disconnect')

      except KeyboardInterrupt:
         Log('Ending track saving')
         logfile.close()
         sys.exit(0)

      except Exception as e:
         Log('Exception accessing tracks: ' + str(e))

      logfile.close()
      # ...and loop we go

# ---------------------------------------
def GetSamples(logfile):
   global LogDuration
   
   url = 'http://localhost/dump1090'
   fieldnames = ['time', 'hex', 'squawk', 'flight', 'lat', 'lon', 'dist', 'altitude', 'mlat',
                 'nucp', 'seen_pos', 'vert_rate', 'track', 'speed', 
                 'messages', 'seen', 'rssi']
   home = pa.read_receiver(url)

   tbgn = datetime.datetime.now()
   now = tbgn;
   writer = csv.DictWriter(logfile, fieldnames=fieldnames, extrasaction='ignore')
   acs = pa.aircraft_loop(url)
   acs = pa.filter_current(acs)
   acs = pa.filter_by_distance(acs, home, 25*5280, 10000)
   for ac in acs: 
      writer.writerow(ac)

      tdelta = datetime.datetime.now() - tbgn
      esec = tdelta.total_seconds()
      if esec > LogDuration: return True

main()
