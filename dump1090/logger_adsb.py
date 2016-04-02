#!/usr/bin/python
# 
# ADS-B display and logging script for dump1090
#
# 2016, Rene Vega
# 2016-03-25, 1.0 - Initial version.
# 2016-04-01, 1.1 - Log read timeouts and other exceptions
# 2016-04-02, 1.2 - Deal with differences in dump1090 mutability
#

import datetime
import json
import requests
import os
import sys
import syslog
import time

Version = '1.2'
Path = os.path.dirname(os.path.realpath(sys.argv[0]))+ '/'

# server connection
URL = ''
PK  = ''

# The requests package will maintain keep-alive connections for a session,
# vastly speeds up HTTP accesses.
S = requests.Session()
print os.path.dirname(os.path.realpath(sys.argv[0]))

# Requires dump1090 --net
GetData = lambda : json.loads(requests.get('http://localhost:8080/data.json').content) # standard dump1090
# GetData = lambda : json.loads(requests.get('http://localhost:8080/data/aircraft.json').content) # dump1090 mutability
Interval = 4.0
ShowSummary = False
ShowDetails = False

def Log(msg):
   print msg
   syslog.syslog(msg)

def SetupServer():
   global PK
   global URL
   # Get the coms auth token
   if os.path.isfile(Path + 'coms_auth'):
      f = open(Path + 'coms_auth');
      PK = f.readline().strip()
      URL = f.readline().strip()
      f.close()
      Log('Coms auth token: ' + PK)
      Log('Coms URL: ' + URL)
   else:
      Log('Server path not setup')


# ---------------------------------
SetupServer();

S = requests.Session()
while True:
   wint = Interval
   where = 'get-adsb'
   try:
      data = GetData()
      nowdt = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
      utcdt = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

      mode_es = 0
      mode_s = 0
      mode_all = 0
      lt15 = 0
      lt10 = 0
      haveflt = 0
      data_es = []

      # Summary stats
      for v in data:
         if abs(v['lat']) > 0.001 or abs(v['lon']) > 0.001: vp = 1
         else: vp = 0
         alt = v['altitude']
         flight = v['flight']
         if vp==1: mode_es = mode_es+1
         if alt!=0:
            mode_s = mode_s+1
            if alt < 15000: lt15 = lt15+1
            if alt < 10000: lt10 = lt10+1
         if flight != '': haveflt = haveflt+1
         mode_all = mode_all+1
      if ShowSummary is True:
         print nowdt, 'all-modes:', mode_all, 'mode-s:', mode_s, 'mode-es:', mode_es, 
         print 'lt 10K:', lt10, 'lt 15K:', lt15, 'flight-IDs:', haveflt 

      # Select only valid position messages
      for v in data:
         squawk = str(v['squawk'])
         flight = str(v['flight'])
         icao = str(v['hex'])
         lat = v['lat']
         lng = v['lon']
         alt = v['altitude']
         trk = v['track']
         spd = v['speed']
         vert = v['vert_rate']
         if vert > 0: vert = '+'+str(vert)
         else: vert = str(vert)
         if abs(lat) > 0.001 and abs(lng) > 0.001:
            if ShowDetails is True:
               print icao, 'sq:'+squawk, str(alt)+'ft', str(trk)+'o', str(spd)+'kt', 'vert:'+vert,
               print ' flight', flight, lat, lng       
            data_es.append(v)
      # If valid messages, log them
      if URL != '' and len(data_es) > 0:
         where = 'post'
         query_args = { 'Action':'Flights', 'PassKey':PK, 'TimeNow':str(utcdt), 'Version':Version,
                        'Summary':{'all-modes':mode_all, 'mode-s':mode_s, 'mode-es':mode_es, 'flight-IDs':haveflt},
                        'Data':data_es }
         response = S.post(URL, data=json.dumps(query_args), timeout=10)
         # Anything other than a 200 status is a deep error condition. Close then reopen the sessions.
         if response.status_code != 200:
            S.close()
            S = requests.Session()
   except Exception, e:
      S.close()
      S = requests.Session()
      try:
         Log('Exception in=' +where +' ' +str(e))
      except:
         Log('Exception in=' +where)
      wint = 2.0

   time.sleep(wint)



