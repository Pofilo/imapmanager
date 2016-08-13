import sys
import yaml

def getParameter(confFile, parameter):
	# Get the parameter in the configuration file
	with open(confFile, 'r') as f:
		conf = yaml.load(f)

	return conf[parameter]
