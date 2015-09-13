#!/bin/sh -e
#

(su -c "sudo bash /home/pi/wifi_monitor.sh" - pi)&
(su -c "sudo python /home/pi/logger_wensn.py" - pi)&
(su -c "sudo python /home/pi/logger_network.py -bkup" - pi)&
exit 0

