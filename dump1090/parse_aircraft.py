# -*- coding: utf-8 -*-

import csv
import json
import math
import requests
import time

from contextlib import closing
from datetime import datetime

rpi2 = 'http://rpi2.local/dump1090'
feet_per_meter = 3.28084
meters_per_mile = 5280/feet_per_meter

S = requests.session()

def filter_by_distance(acs, home, max_dist_feet, max_altitude_feet):
    for ac in acs:
        dist = greatcircle(home[0], home[1], ac['lon'], ac['lat']) * feet_per_meter
        dist = int(dist)
        if dist <= max_dist_feet and ac['altitude'] < max_altitude_feet:
            ac['dist'] = dist
            yield ac
            
def filter_current(acs):
    ''' Filter aircraft to ones with current lat lon and altitude data.
        Replace mlat dict with flag'''
    for ac in acs:
        if ac['seen'] > 15 or (ac.has_key('seen_pos') and ac['seen_pos'] > 15):
            continue
        if not ac.has_key('lat') or not ac.has_key('altitude'):
            continue
        if ac.has_key('mlat'):
            ac['mlat'] = 1
        else:
            ac['mlat'] = 0
        yield ac

def aircraft(parsed_json):
    ''' Given the parsed json from aircraft.json, iterate the actual aircraft.
        Add a datetime time stamp to each. '''
    now = parsed_json['now']
    for ac in parsed_json['aircraft']:
        ac['time'] = now
        yield ac

def aircraft_loop(url):
    ''' Read and parse aircraft in a loop '''
    previous = 0
    while 1:
        json = read_aircraft(url)
        if json:
            now = json['now']
            if now > previous:
                print now
                for ac in json['aircraft']:
                    ac['time'] = now
                    yield ac
        time.sleep(1)
        
def read_receiver(url):
    r = S.get(url + '/data/receiver.json')
    if r.status_code != requests.codes.ok:
        return
    
    receiver = r.json()
    if receiver.has_key('lat'):
        rlat = float(receiver['lat'])
        rlon = float(receiver['lon'])
    else:
        rlat = rlon = None
    
    return (rlon, rlat)


def read_aircraft(url):
    r = S.get(url + '/data/aircraft.json')
    if r.status_code != requests.codes.ok:
        return

    return r.json()

# From https://github.com/mutability/dump1090-tools/blob/master/collectd/dump1090.py
def greatcircle(lon0, lat0, lon1, lat1):
    ''' Great circle distance between two points. '''
    lat0 = lat0 * math.pi / 180.0;
    lon0 = lon0 * math.pi / 180.0;
    lat1 = lat1 * math.pi / 180.0;
    lon1 = lon1 * math.pi / 180.0;
    return 6371e3 * math.acos(math.sin(lat0) * math.sin(lat1) + math.cos(lat0) * math.cos(lat1) * math.cos(abs(lon0 - lon1)))

if __name__ == '__main__':
    import pprint
    home = read_receiver(rpi2)

    with open('tracks.csv', 'w') as csvfile:
        fieldnames = ['time', 'hex', 'squawk', 'flight', 'lat', 'lon', 'dist', 'altitude', 'mlat',
                      'nucp', 'seen_pos', 'vert_rate', 'track', 'speed', 
            'messages', 'seen', 'rssi']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')

        writer.writeheader()

        acs = aircraft_loop(rpi2)
        acs = filter_current(acs)
        acs = filter_by_distance(acs, home, 25*5280, 10000)
        for ac in acs: writer.writerow(ac)
