# Fabric file to help with deployment
from __future__ import with_statement

from fabric.api import *
from fabric.decorators import hosts

import os
from StringIO import StringIO

env.hosts = ['kent37pi.local', '10.0.0.250']
env.user = 'pi'
env.key_filename = '~/.ssh/id_rsa.pub'

@task
@hosts('kent37pi.local')
def count_new_logs():
	''' Count the number of logs which have not been downloaded yet. '''
	print len(find_new_logs()), ' new logs'

@task
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

@task
@hosts('10.0.0.250')
def count_new_tracks():
	''' Count the number of tracks which have not been downloaded yet. '''
	print len(find_new_tracks()), ' new tracks'

local_track_dir = '/Volumes/TRACKS/'

@task
@hosts('10.0.0.250')
def get_new_tracks():
	''' Download all new tracks. '''
	new_tracks = find_new_tracks()
	print 'Fetching', len(new_tracks), ' new tracks'
	with cd('/home/pi/logger/tracks'), lcd(local_track_dir):
		for track in new_tracks:
			print track
			get(remote_path=track, local_path=track)

def find_new_tracks():
	''' Get a list of tracks on the remote not on local. '''
	local_tracks = set(os.listdir(local_track_dir))
	with cd('/home/pi/logger/tracks'):
		myout = StringIO()
		output = run('ls', stdout=myout)
		output = output.split()
		output = [f for f in output if f not in local_tracks]
		return output
