# Access to the actual noise data
import os

import web
import config

from datetime import datetime, timedelta
from itertools import izip_longest

# At least one of these directories must exist. We will look in both
log_path = os.path.join(config.base_path, 'logs')
bkup_path = os.path.join(config.base_path, 'bkup')

date_format = '%Y-%m-%d %H:%M:%S'

def dates():
	""" Return a sorted list of all available dates """
	dates = dates_for(bkup_path) | dates_for(log_path)
	dates = list(dates)
	dates.sort()
	return dates

def dates_for(path):
	""" Find all dates in one directory """
	if not os.path.exists(path):
		return set()
	files = os.listdir(path)
	dates = set(file[4:14] for file in files if file.startswith('Log'))
	return dates

def date_data(date):
	""" Return the data for one date as csv """
	files = date_files(bkup_path, date) + date_files(log_path, date)
	return parse_data(files)

def date_files(path, date):
	""" All files for one date in path. Returns full paths.
	    We use the start date of each file as its date so the date boundary is not at midnight. """
	if not os.path.exists(path):
		return list()
	filter = 'Log_' + date
	files = os.listdir(path);
	files = [file for file in files if file.startswith(filter)]
	files = [os.path.join(path, file) for file in files]
	files.sort()
	return files

# From itertools recipes
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)

def parse_data(files):
	""" Parse a list of files. Returns an iterable of lines with just a timestamp and value. """
	for file in files:
		with open(file, 'r') as inp:
			for line in inp:
				data = line.split(',')
				if len(data) == 9:
					date = data[0][:19] # Date and time without msec
					avg = (float(data[7]) + float(data[8]))/2 # Average the two noise readings
					yield '%s,%s\r\n' % (date, avg)
				elif len(data) > 9:
					version = float(data[1]) # Should be 2.0
					date = data[0][:19] # Date and time without msec
					dt = datetime.strptime(date, date_format)
					readings = list(map(float, data[8:]))
					for pair in grouper(readings, 2):
						avg = sum(pair)/len(pair)
						yield '%s,%s\r\n' % (dt.strftime(date_format), avg)
						dt += timedelta(seconds=1)