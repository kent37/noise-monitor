#!/bin/bash
# 2015-09-21, Add ethernet interface checks.
# 2015-12-25, Increase the down time sleep delay, some WiFi dongles take longer to reset.

timestamp() {
  date +"%Y-%m-%d_%H:%M:%S"
}

log() {
  echo "$(timestamp) $1"
  logger "$(timestamp) $1"
}

# This script is a workaround hack for the dropped connection
# bug in Debian/Raspbian WIFI stack. It checks the network status
# periodically and forces wlan0 to enable when it finds it down.
# This also checks for ethernet access, finding it connected, 
# it skips the wifi check.
log "WIFI monitor started"
while true ; do
   # If ethernet connected, skip the wifi checks
   if ifconfig eth0 | grep -q "inet addr:"; then
      sleep 20
   # if Wifi is connected, check again later.
   elif ifconfig wlan0 | grep -q "inet addr:" ; then
      sleep 20
   else
      # Wifi and ethernet is down.
      ifdown --force wlan0
      sleep 1
      log "WIFI connection down! Reconnecting."
      ifup --force wlan0
      sleep 20
   fi
done

