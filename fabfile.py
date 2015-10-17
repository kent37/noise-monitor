# Fabric file to help with deployment
from __future__ import with_statement

from fabric.api import *
from fabric.decorators import hosts

import os
from StringIO import StringIO

env.hosts = ['kent37pi.local', 'rpi2.local']
env.user = 'pi'
env.key_filename = '~/.ssh/id_rsa.pub'

@hosts('kent37pi.local')
def count_new_logs():
	''' Count the number of logs which have not been downloaded yet. '''
	print len(find_new_logs()), ' new logs'

@hosts('kent37pi.local')
def get_new_logs():
	''' Download all new logs. '''
	new_logs = find_new_logs()
	print 'Fetching', len(find_new_logs()), ' new logs'
	with cd('/home/pi/logger/bkup'), lcd('../logs'):
		for log in new_logs:
			print log
			get(remote_path=log, local_path=log)

def find_new_logs():
	''' Get a list of logs on the remote not on local. '''
	local_logs = set(os.listdir('../logs'))
	with cd('/home/pi/logger/bkup'):
		myout = StringIO()
		output = run('ls', stdout=myout)
		output = output.split()
		output = [f for f in output if f not in local_logs]
		return output
