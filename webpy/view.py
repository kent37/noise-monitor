import os

import web
import config

def dates(path):
	""" Return all the available dates """
	files = os.listdir(path)
	dates = set(file[4:14] for file in files if file.startswith('Log'))
	dates = list(dates)
	dates.sort()
	return dates

def date_data(date):
	""" Return the data for one date as csv """
	filter = 'Log_' + date
	files = os.listdir(config.base_path);
	files = [file for file in files if file.startswith(filter)]
	return parse_data(files)

def parse_data(files):
	for file in files:
		path = os.path.join(config.base_path, file)
		with open(path, 'r') as inp:
			for line in inp:
				data = line.split(',')
				if len(data) == 9:
					date = data[0]
					avg = (float(data[7]) + float(data[8]))/2
					yield '%s,%s' % (date, avg)