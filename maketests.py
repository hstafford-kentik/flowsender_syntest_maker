#!/usr/bin/python3

import string
import time
import subprocess
import json
import requests
import configparser
import re
import threading
import pprint

pp = pprint.PrettyPrinter(indent=1)
config = configparser.ConfigParser() 
	
def getSendingIPs():  #get list of devices from the API
	with open('/etc/default/kentik.env', 'r') as f:
		config_string = '[DEFAULT]\n' + f.read()
	f.close()
	config.read_string(config_string)
	defaultConfig = config['DEFAULT']
	payload = {'Content-Type': 'application/json', 'X-CH-Auth-API-Token':defaultConfig["KENTIK_API_TOKEN"], 'X-CH-Auth-Email':defaultConfig["KENTIK_API_EMAIL"]}
	rkentik = requests.get('https://api.kentik.com/api/v5/devices', headers = payload)
	#print (rkentik.text)
	return json.loads(rkentik.text)

def findMyID():
	global agentID
	agentID = 0
	process = subprocess.Popen(["journalctl -r -u ksynth.service --no-pager | grep 'authenticated agent'"], shell=True, stdout=subprocess.PIPE)
	while agentID == 0:
		line = process.stdout.readline()
		line = line.decode('utf-8')
		found = re.findall(" authenticated agent \d+", line)
		found2 = re.findall("\d+", found[0])
		agentID = int(found2[0])
		
def createTest(targetIP,agentID,testName):  #create a simple test with these variables
	with open('/etc/default/kentik.env', 'r') as f:
		config_string = '[DEFAULT]\n' + f.read()  ## because kentik.env doesn't have the 'proper' format
	f.close()
	config.read_string(config_string)
	defaultConfig = config['DEFAULT']
	payload = {'Content-Type': 'application/json', 'X-CH-Auth-API-Token':defaultConfig["KENTIK_API_TOKEN"], 'X-CH-Auth-Email':defaultConfig["KENTIK_API_EMAIL"]}
	template = """
	{
	"test": {
		"name": "<TEST_NAME>",
		"settings": {
			"agentIds": ["<AGENT_ID>"],
			"family": "IP_FAMILY_DUAL",
			"healthSettings": {
				"dnsValidCodes": [],
				"httpLatencyCritical": 0,
				"httpLatencyCriticalStddev": 3,
				"httpLatencyWarning": 0,
				"httpLatencyWarningStddev": 1.5,
				"httpValidCodes": [],
				"jitterCritical": 0,
				"jitterCriticalStddev": 3,
				"jitterWarning": 0,
				"jitterWarningStddev": 1.5,
				"latencyCritical": 0,
				"latencyCriticalStddev": 3,
				"latencyWarning": 0,
				"latencyWarningStddev": 1.5,
				"packetLossCritical": 60,
				"packetLossWarning": 21,
				"unhealthySubtestThreshold": 1
			},
			"ip": {
				"targets": ["<IP_ADDRESS>"]
			},
			"notificationChannels": [],
			"period": 60,
			"ping": {
				"count": 5,
				"delay": 100,
				"port": 443,
				"protocol": "icmp",
				"timeout": 3000
			},
			"tasks": ["ping", "traceroute"],
			"trace": {
				"count": 3,
				"delay": 100,
				"limit": 30,
				"port": 33434,
				"protocol": "udp",
				"timeout": 22500
			}
		},
		"status": "TEST_STATUS_ACTIVE",
		"type": "ip"
	}
	}"""
	# Yep, there are 10 better ways to do this, but it logically makes sense to me.
	template = template.replace("<IP_ADDRESS>", targetIP)
	template = template.replace("<AGENT_ID>", str(agentID))	
	template = template.replace("<TEST_NAME>", testName)	
	rkentik = requests.post('https://grpc.api.kentik.com/synthetics/v202202/tests', headers = payload,json=json.loads(template))
	#print (rkentik.text)  # debugging
	return json.loads(rkentik.text)

def getTest():  #get test from the API
	with open('/etc/default/kentik.env', 'r') as f:
		config_string = '[DEFAULT]\n' + f.read()
	f.close()
	config.read_string(config_string)
	defaultConfig = config['DEFAULT']
	payload = {'Content-Type': 'application/json', 'X-CH-Auth-API-Token':defaultConfig["KENTIK_API_TOKEN"], 'X-CH-Auth-Email':defaultConfig["KENTIK_API_EMAIL"]}

	rkentik = requests.get('https://grpc.api.kentik.com/synthetics/v202202/tests/21667', headers = payload)
	#print (rkentik.text)
	return json.loads(rkentik.text)


#pp.pprint(getTest())

#First check to make sure ksynth is running
output = subprocess.getoutput('ps aux | grep ksynth ')
if 'ksynth agent' not in output:
	print ('It seems that ksynth agent is not running on this server.  Please complete')
	print ('the ksynth setup and registration at https://portal.kentik.com/v4/synthetics/agents')
	print ()

		
# Using threading here because parsing journalctl can take a while and blocks progress
t = threading.Thread(target=findMyID)
agentID = 0
t.start()

while agentID == 0:  # chill out until the threaded process finds the agent ID in journal
    print ('Searching journalctl for agentID')
    time.sleep(2)
print ('Agent ID is '+str(agentID))

print ('Getting list of device sending IPs from API.')
devices = getSendingIPs()
for device in devices['devices']:
	print('Found '+device['device_name']+ ' with device ID '+str(device['id']))
	count = 0
	for ip in device['sending_ips']:
		response = False
		process = subprocess.Popen(['ping -c 3 '+ip], shell=True, stdout=subprocess.PIPE)
		print ('Ping testing '+ip)
		try:
			output = subprocess.getoutput('ping -c 3 '+ip)
			if ' bytes from ' in output:
				response = True
			else:
				response = False
		except:
			response = False
		if response == True:
			print (ip+' responded to a ping!')
			count+=1
			testName = 'Flow Sender '+device['device_name']+' IP '+str(count)
			print('Creating test: '+testName+' on IP address '+ip)
			createTest(ip,agentID,testName)
		else:
			print (ip+' did not respond.  Skipping adding a synth test for this one.')
	print('---------------------------')

exit()


