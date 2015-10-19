https://github.com/mutability/dump1090/blob/master/README-json.md

## aircraft.json

This file contains dump1090's list of recently seen aircraft. The keys are:

 * now: the time this file was generated, in seconds since Jan 1 1970 00:00:00 GMT (the Unix epoch).
 * messages: the total number of Mode S messages processed since dump1090 started.
 * aircraft: an array of JSON objects, one per known aircraft. Each aircraft has the following keys. Keys will be omitted if data is not available.
   * hex: the 24-bit ICAO identifier of the aircraft, as 6 hex digits. The identifier may start with '~', this means that the address is a non-ICAO address (e.g. from TIS-B).
   * squawk: the 4-digit squawk (octal representation)
   * flight: the flight name / callsign
   * lat, lon: the aircraft position in decimal degrees
   * nucp: the NUCp (navigational uncertainty category) reported for the position
   * seen_pos: how long ago (in seconds before "now") the position was last updated
   * altitude: the aircraft altitude in feet, or "ground" if it is reporting it is on the ground
   * vert_rate: vertical rate in feet/minute
   * track: true track over ground in degrees (0-359)
   * speed: reported speed in kt. This is usually speed over ground, but might be IAS - you can't tell the difference here, sorry!
   * messages: total number of Mode S messages received from this aircraft
   * seen: how long ago (in seconds before "now") a message was last received from this aircraft
   * rssi: recent average RSSI (signal power), in dbFS; this will always be negative.
