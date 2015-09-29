# Core logger of the RPI
# 2015, Rene Vega

import datetime
import time
import sys
import os

Version = '1.0'
Path = Version = '2.0'
Path = os.path.dirname(os.path.realpath(sys.argv[0])) + '/'

def main():
   global Version
   global Path

   # Create the core directory if not found
   dir = Path + 'core/'
   if not os.path.exists(dir):
      os.makedirs(dir)

   while True:
      # Make the log name, then open it.
      dt = str(datetime.datetime.now()).replace(' ','_')
      logname = dir + 'Core_' + dt
      print 'getting core-data & logging to: ', logname
      logfile = open(logname, 'a')

      # Gather the data, sampling periodically.
      try:
         if GetSamples(logfile) == False:
            print '/nSampling ended'
            logfile.close()
            sys.exit(0)

      except KeyboardInterrupt:
         print 'Ending sampling'
         logfile.close()
         sys.exit(0)

      logfile.close()
      print 'Restarting data collection'
      # ...and loop we go

# ---------------------------------------
def GetSamples(logfile):
   tbgn = datetime.datetime.now()
   while True:
      now = datetime.datetime.now()

      # Grab temperature data
      temp = os.popen('vcgencmd measure_temp').readline()
      temp = temp.replace('temp=', '').replace("'C\n","")
      tempf = float(temp) * 9.0 / 5.0 + 32.0
      tempf = str(tempf);

      # Grab voltage data
      volts = os.popen('vcgencmd measure_volts').readline()
      volts = volts.replace('volt=', '').replace("V\n", "")

      # Grab frequency data
      freqc = os.popen('vcgencmd measure_clock core').readline()
      freqc = freqc.replace('frequency(1)=', '').replace('\n', '')
      freqc = str(float(freqc) / 1000000)

      freqa = os.popen('vcgencmd measure_clock arm').readline()
      freqa = freqa.replace('frequency(45)=', '').replace('\n', '')
      freqa = str(float(freqa) / 1000000)
      print temp+"C", tempf+"F", volts+"V", freqc+"MHz", freqa+"MHz"

      # Write a log entry: datetime,temp
      # Flush the buffer on every write to ensure the network logger sees timely data
      logentry = str(datetime.datetime.now())+','+temp+','+tempf+','+volts+','+freqc+','+freqa+'\n'
      logfile.write(logentry)
      logfile.flush()
      
      tdelta = now - tbgn
      esec = tdelta.total_seconds()
      if esec > 7200: return True

      time.sleep(5)

main()
