# Sound/Noise logger - updater
# 2015-10-02, Rene Vega
#
# This applet is the auto updater for the noise monitor system.
# It is invoked by the logger_network applet whenever it receives
# an update response.
#
# 2015-10-02: 1.0
# 2015-11-24: 1.1 - Fix toggle-wlan0 action.
# 2015-01-16, 1.2 - Add completion notify, sequence number and refid logic
# 2015-01-18, 1.3 - Add error checking on params
# 2016-01-22, 1.4 - Make this a standalone updater.
# 2016-01-25, 1.5 - Missed wrapping one HTTP call with exception catcher.
# 2016-01-26, 1.6 - Longer timeouts
# 2016-03-08, 1.7 - Wrap actions with exception handlers
# 2016-03-10, 1.8 - Add version to the 'check' request.
#

import time
import logging
import json
import ssl
import requests
import os
import datetime
import signal
import sys
import syslog
import subprocess

Version = '1.8'
Path = os.path.dirname(os.path.realpath(sys.argv[0]))+ '/'

# server connection
URL = 'https://skyote.com/nl/nl-serverj.php'
PK  = '569gksxi4e7883,r60etgv-10d'
RefID = ''

# do not run if parameter passed
if len(sys.argv) > 1: sys.exit(0)

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

	# Get the coms auth token
	if os.path.isfile(Path + 'coms_auth'):
		f = open(Path + 'coms_auth');
		PK = f.readline().strip()
		URL = f.readline().strip()
		f.close()
		Log('Coms auth token: ' + PK)
		Log('Coms URL: ' + URL)


	action = ''

	# Get the reference ID associated with this noise monitor.
	serial = GetSerial()
	while True:
		# Log in using the Raspberry PI's serial number. A reference ID is returned
		query_args = { 'Action':'data-login', 'Serial':serial, 'PassKey':PK }
		try:
			response = S.post(URL, data=json.dumps(query_args), timeout=30)
		except Exception, e:
			time.sleep(10)
			continue;
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

	Log('Updater version: ' + Version)

	# Check for updates every two minutes when nothing is pending.
	while True:
		if (CheckServerActions()): time.sleep(0.1)
		else: time.sleep(60)

# Check server for actions
def CheckServerActions():
	global Version
	global Path
	global S
	global URL
	global PK
	global RefID

	query_args = { 'Action':'Check', 'PassKey':PK, 'Ref_ID':RefID, 'Version':Version }
	try:
		response = S.post(URL, data=json.dumps(query_args), timeout=30)
	except KeyboardInterrupt:
		print '\nQuitting'
		sys.exit(1)
	except Exception, e:
		Log('HTTP Request exception: ' + str(e))
		S = requests.Session()
		return False

	if response.status_code == 200:
		jresp = json.loads(response.content)
		jstat = jresp['Status']
		if jstat == 'More':
			action = jresp['Action'] # a json string
			DoServerAction(action);
			return True

	return False

def DoServerAction(jresp):
	global Version
	global Path
	global S
	global URL
	global PK
	global RefID

	jresp = json.loads(jresp)
	action = jresp['Action']
	
	Log('Updater - Action: ' + action)
	if action == 'reboot' or action == 'Reboot':
		NotifyActionCompleted('reboot')
		time.sleep(3)
		ipa = subprocess.check_output(['sudo','reboot'], stderr=subprocess.STDOUT)
	elif action == 'toggle-wlan0':
		ipa = subprocess.check_output(['sudo','ifdown','wlan0'], stderr=subprocess.STDOUT)
		ipa = subprocess.check_output(['sudo','ifup','wlan0'], stderr=subprocess.STDOUT)
		NotifyActionCompleted(ipa)
	elif action == 'clear-bkup':
		try:
			ipa = subprocess.check_output(['sudo','rm', Path + '/bkup/*'], stderr=subprocess.STDOUT)
		except:
			ipa = ''
			pass
		NotifyActionCompleted(ipa)
	elif action == 'run':
		try:
			fname = jpresp['Fname']
			ipa = subprocess.check_output([fname], stderr=subprocess.STDOUT)
		except:
			ipa = ''
			pass
		NotifyActionCompleted(ipa)
	elif action == 'write-file':
		try:
			fname = jresp['Fname']
			content = jresp['content']
			ipa = 'Not opened'
			f = open(fname, 'w')
			ipa = 'Not written'
			f.write(content);
			f.close()
			ipa = ''
		except: pass
		Log('write-file ' +fname + ' stat=' + ipa);
		NotifyActionCompleted(ipa)
	elif action == 'sudo-write-file':
		try:
			fname = jresp['Fname']
			content = jresp['content']
			ipa = 'Not opened'
			f = open(Path +'tempfile.txt', 'w')
			ipa = 'Not written'
			f.write(content);
			f.close()
			ipa = 'temp created'
			ipa = subprocess.check_output(['sudo','cp', '-f',Path +'tempfile.txt',fname], stderr=subprocess.STDOUT)
			os.remove(Path +'tempfile.txt')
		except: pass
		Log('sudo-write-file ' +fname + ' stat=' + ipa);
		NotifyActionCompleted(ipa)
	elif action == 'say':
		try:
			Log(jresp['Text']);
		except: pass
		NotifyActionCompleted('')

	else:
		NotifyActionCompleted('Invalid action')
	return

# Notify completion
def NotifyActionCompleted(resp):
	global Version
	global Path
	global S
	global URL
	global PK
	global RefID

	query_args = { 'Action':'Completed', 'PassKey':PK, 'Ref_ID':RefID, 'Response':resp, 'Version':Version }
	try:
		response = S.post(URL, data=json.dumps(query_args), timeout=30)
	except KeyboardInterrupt:
		print '\nQuitting'
		sys.exit(1)
	except Exception, e:
		Log('HTTP Request exception: ' + str(e))
		S = requests.Session()
		return
	resp = response.content
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
