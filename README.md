# flowsender_syntest_maker
Simple python script to add synthetic tests for each flow sender in an account

Basically, just put this script anywhere and ./maketests.py   
Assuming that kproxy AND a ksynth private agent is installed on this server, it will pull the API key 
from /etc/default/kentik.env just like kproxy does.  No configuration is required beyond installing kproxy
and ksynth.  (ksynth must be currently running and registered)

It will pull the flow-sending device list from the API, make sure the IP(s) respond to pings, and then
create a simple ICMP test for each IP address that responds.  Unfortunately, the API does not support notifications
yet, so those will need to be configured manually in the portal.


