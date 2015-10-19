# -*- coding: utf-8 -*-

import json
import math
import requests

from contextlib import closing

rpi2 = 'http://rpi2.local/dump1090'
S = requests.session()

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
def greatcircle(lat0, lon0, lat1, lon1):
    ''' Great circle distance between two points. '''
    lat0 = lat0 * math.pi / 180.0;
    lon0 = lon0 * math.pi / 180.0;
    lat1 = lat1 * math.pi / 180.0;
    lon1 = lon1 * math.pi / 180.0;
    return 6371e3 * math.acos(math.sin(lat0) * math.sin(lat1) + math.cos(lat0) * math.cos(lat1) * math.cos(abs(lon0 - lon1)))

#    for a in aircraft_data['aircraft']:
#        if a['seen'] < 15: total += 1        
#        if a.has_key('seen_pos') and a['seen_pos'] < 15:
#            with_pos += 1
#            if rlat is not None:
#                distance = greatcircle(rlat, rlon, a['lat'], a['lon'])
#                if distance > max_range: max_range = distance
#            if 'lat' in a.get('mlat', ()):
#                mlat += 1
