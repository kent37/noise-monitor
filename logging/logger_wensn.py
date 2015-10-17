# Sound/noise logger for WENSN 1361 meter
# 2015, Rene Vega
# 2015-09-22, Add logging to var/log/messages
# 2015-09-22, Add version control
# 2015-09-23, Add batched samples to speed up catchup mode and to lower the physical write rate.
# 2015-09-30, fix missing ","

import datetime
import time
import sys
import usb.core
import os
import syslog

Version = '2.1'
Path = os.path.dirname(os.path.realpath(sys.argv[0])) + '/'

def Log(msg):
   print msg
   syslog.syslog(msg)

def main():
   global Version
   global Path

   Log('WENSN meter logger started, version: ' + Version)

   # Print all usb devices (diagnostic)
   dev = usb.core.find(find_all=True)
   for cfg in dev:
      sys.stdout.write('vid=' +hex(cfg.idVendor) +' pid=' +hex(cfg.idProduct) +'\n')

   # Create the Log directory if not found
   dir = Path + 'logs/'
   if not os.path.exists(dir):
      os.makedirs(dir)

   while True:
      # Locate the WENSN meter. If it is not found do a slow poll looking for it.
      Log('Locating WENSN meter...')
      dev = None

      try:
         while dev is None:
            dev = usb.core.find(idVendor=0x16c0, idProduct=0x5dc) # WENSN
            if dev is not None:
               print 'device found'
               break
            time.sleep(1.0)
      except KeyboardInterrupt:
         print '\nEnding search'
         sys.exit(0)

      dev.set_configuration()

      # Make the log name, then open it.
      dt = str(datetime.datetime.now()).replace(' ','_')
      logname = dir + 'Log_' + dt
      Log('Logging to: ' + logname)
      logfile = open(logname, 'a')

      # Gather the meter data, sampling twice a second.
      # Also decode the meter options
      try:
         if GetSamples(dev,logfile) == False:
            Log('/nMeter glitch or disconnect')

      except KeyboardInterrupt:
         Log('Ending noise sampling')
         logfile.close()
         sys.exit(0)

      except Exception as e:
         Log('Exception accesing meter: ' + str(e))


      logfile.close()
      # ...and loop we go

# ---------------------------------------
def GetSamples(dev,logfile):
   batchsize = 10
   tbgn = datetime.datetime.now()
   now = tbgn;
   dbi = 0
   db = []
   while True:
      opts = ''
      meter = 'WENSN 1361'
      weight = ''
      rate  = ''
      mode  = ''
      range = ''

      # Grab meter data
      ret = dev.ctrl_transfer(0xC0, 4, 0, 0, 2, 1000)
      if ret is None: return False

      # Decode the options flags
      ro = ret[1] & 0xfc
      if (ro&0x20) != 0: weight='C'
      else:              weight='A'
      if (ro&0x40) != 0: rate ='slow'
      else:              rate ='fast'
      if (ro&0x80) != 0: mode ='max'
      else:              mode = 'samp'

      # Decode the range settings
      ro = ro & 0x1f
      if   ro == 0x00: range ='30-80db'
      elif ro == 0x04: range ='40-90db'
      elif ro == 0x08: range ='50-100db'
      elif ro == 0x0c: range ='60-110db'
      elif ro == 0x10: range ='70-120db'
      elif ro == 0x14: range ='80-130db'
      elif ro == 0x18: range ='30-130db'
      opts = weight +','+rate +','+mode +','+range

      # Decibels is a 10-bit value with zero representing 30db
      db.append((ret[0] + ((ret[1] & 3) * 256)) * 0.1 + 30)
      dbi += 1

      # Combine 10 samples for a 5-second interval
      if dbi >= batchsize:
         print ','.join([str(item) for item in db[0:]]), ' (', opts, ') raw=', str(bytearray(ret)).encode('hex')

         # Write a log entry: datetime,version,meter_type,weight,rate,mode,range,num_samples,samp1,samp2,...
         # Flush the buffer on every write to ensure the network logger sees timely data
         # logentry = str(datetime.datetime.now())+','+Version+','+meter+','+opts+','+str(dbi)+','+str(db[0])+','+str(db[1])+'\n'
         logentry = str(now)+','+Version+','+meter+','+opts+','+str(dbi)+','+','.join([str(item) for item in db[0:]])+'\n'
         logfile.write(logentry)
         logfile.flush()
         now = datetime.datetime.now()
         dbi = 0
         db = []

      tdelta = now - tbgn
      esec = tdelta.total_seconds()
      if esec > 7200: return True

      time.sleep(0.5)

main()
