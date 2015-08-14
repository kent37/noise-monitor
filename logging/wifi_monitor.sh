#!/bin/bash

timestamp() {
  date +"%Y-%m-%d_%H-%M-%S"
}

# This script is a workaround hack for the dropped connection
# bug in Debian/Raspbian WIFI stack. It checks the network status
# periodically and forces wlan0 to enable when it finds it down.
while true ; do
   if ifconfig wlan0 | grep -q "inet addr:" ; then
      sleep 20
   else
      echo "$(timestamp) WIFI connection down! Reconnecting."
      ifup --force wlan0
      sleep 10
   fi
done
