# -*- coding: utf-8 -*-
'''
Beacon to transmit exceeding diskstat threshold
'''

# Import Python libs
from __future__ import absolute_import
import logging
import os
import re

# Import Salt libs
import salt.utils

# Import Py3 compat
from salt.ext.six.moves import zip

log = logging.getLogger(__name__)

__virtualname__ = 'iostat'

def __virtual__():
    if salt.utils.is_windows():
        return False
    else:
        return __virtualname__

def read_stats_file(file):
	s = ""
	count = 0
	with open(file,"r") as f:
		for line in f:
			s+=line
	return (s)

def dict_data(string,match_re,exclude_re):
	data_dict={}
	for line in string.splitlines():
		line_dict = line.strip().split()
		dev_name = line_dict[2]
		if ( len(match_re) >0 or len(exclude_re) >0):
			if ((re.match(exclude_re,dev_name)) and (len(exclude_re) > 0)):
				continue
			elif ((re.match(match_re,dev_name)) and (len(match_re) > 0)):
				data_dict[dev_name]=line_dict
			elif (re.match('^sd.*[a-z]$',dev_name)):
				data_dict[dev_name]=line_dict
			else:
				continue
		else:
			if (re.match('^sd.*[a-z]$',dev_name)):
				data_dict[dev_name]=line_dict
	
	return data_dict

def calculate(ret,org_dict,new_dict):
#	await: (read_ms f4+write_ms f8)/(f1 read +f5 write)
#	stime: (ms_spent f10 / (f1+f2+f5+f6  read+read_merge_write_write_merge)
	data={}
	for key in org_dict:
		if ( (len(org_dict[key]) != 14) or (len(new_dict[key]) != 14)):
			ret.append({'tag': 'error', 'ERROR': 'Disk stats short array' })
			continue
		if key in new_dict:
			data[key]={}
			data[key]['read']=int(new_dict[key][3]) - int(org_dict[key][3])
			data[key]['read_merge']=int(new_dict[key][4]) - int(org_dict[key][4])
			data[key]['read_sectors']=int(new_dict[key][5]) - int(org_dict[key][5])
			data[key]['read_ms']=int(new_dict[key][6]) - int(org_dict[key][6])
			data[key]['write']=int(new_dict[key][7]) - int(org_dict[key][7])
			data[key]['write_merge']=int(new_dict[key][8]) - int(org_dict[key][8])
			data[key]['write_sectors']=int(new_dict[key][9]) - int(org_dict[key][9])
			data[key]['write_ms']=int(new_dict[key][10]) - int(org_dict[key][10])
			data[key]['org_active_io']=int(org_dict[key][11])
			data[key]['new_active_io']=int(new_dict[key][11])
			data[key]['io_ticks']=int(new_dict[key][12]) - int(org_dict[key][12])
			data[key]['queue_ms']=int(new_dict[key][13]) - int(org_dict[key][13])
			if data[key]['read'] <= 0:
				data[key]['read_await']=0
			else:
				data[key]['read_await']=data[key]['read_ms'] / float(data[key]['read'])
			if data[key]['write'] <= 0:
				data[key]['write_await']=0
			else:
				data[key]['write_await']=data[key]['write_ms'] / float(data[key]['write'])
			if (data[key]['write']+data[key]['read']) <=0:
				data[key]['await']=0
			else:
				data[key]['await']=(data[key]['read_ms']+data[key]['write_ms']) / float((data[key]['read']+data[key]['write']))
			if (data[key]['read']+data[key]['write']+data[key]['read_merge']+data[key]['write_merge']) <=0:
				data[key]['stime']=0
			else:
				data[key]['stime'] = data[key]['io_ticks'] / float((data[key]['read']+data[key]['write']+data[key]['read_merge']+data[key]['write_merge']))
	
	return (ret,data)

def validate(config):
	VALID_FIELDS = ['read','read_merge','read_sectors','read_ms','write','write_merge','write_sectors','write_ms','org_active_io','new_active_io','io_ticks','queue_ms','read_await','write_await','await','stime']


	# Configuration for load beacon should be a list of dicts
	if not isinstance(config, dict):
		log.info('Configuration for load beacon must be a dictionary.')
		return False
	else:
		for item in config:
			if not isinstance(config[item], dict):
				log.info('Configuration for iostat beacon must '
					'be a dictionary of dictionaries.')
				return False
			else:
				if not any(key in VALID_FIELDS for j in config[item]):
					log.info('Invalid configuration item in iostat beacon config')
					return False
	return True

def beacon(config):
	ret = []
	global PREVIOUS_IOSTATS
	FILENAME='/proc/diskstats'
	DEFAULT_THRESHOLD=20
	DEFAULT_FIELD='await'

	if 'match_re' not in config:
		config['match_re']='^sd.*[a-z]$'
	if 'exclude_re' not in config:
		config['exclude_re']=''
	if 'output' not in config:
		config['output']='default'
	if 'fields' not in config:
		config['fields']={}
		config['fields'][DEFAULT_FIELD]=DEFAULT_THRESHOLD
		
	for key in config['fields']:
		if key not in config['fields']:
			config['fields'][key]=DEFAULT_THRESHOLD
		if config['fields'][key] <=0:
			config['fields'][key]=DEFAULT_THRESHOLD

	match_re=config['match_re']
	exclude_re=config['exclude_re']
	log.trace('load beacon starting')
	try:
		PREVIOUS_IOSTATS
	except NameError:
		PREVIOUS_IOSTATS= read_stats_file(FILENAME)
		ret.append({'tag': 'startup', 'config': config})
		return ret
	else:
		old_data=PREVIOUS_IOSTATS
	
	new_data = read_stats_file(FILENAME)

	if len(new_data) > 0:
		PREVIOUS_IOSTATS=new_data
	else:
		ret.append({'tag': 'error', 'text': 'Unable to read new stats' })

	new_dict = dict_data(new_data,config['match_re'],config['exclude_re'])
	org_dict = dict_data(old_data,config['match_re'],config['exclude_re'])

	(ret,state) = calculate(ret,org_dict,new_dict)
	threshold={}
	threshold_values={}
	for key in state:
		found=0
		for key2 in config['fields']:
			if (state[key][key2] >= int(config['fields'][key2])):
				if key not in threshold:
					threshold[key]={}
				threshold[key][key2]=int(config['fields'][key2])
				if (config['output'] == 'full'):
					threshold_values[key]=state[key]
				else:
					if key not in threshold_values:
						threshold_values[key]={}
					threshold_values[key][key2]=state[key][key2]
					
				found=1
		if found !=0:
			ret.append({'tag': 'threshold', 'thresholds': threshold, 'values': threshold_values })
	return ret
