import sys
import yaml

def getParameter(confFile, parameter):
	# Get the parameter in the configuration file
	conf = openYaml(confFile)

	return conf[parameter]

def openYaml(confFile):
	# Open and return the yaml file
	with open(confFile, 'r') as f:
		return yaml.load(f)

def getFolder(confFile, mailTo):
	conf = openYaml(confFile)
	for k,v in conf["to"].iteritems():
		if k.find(mailTo) != -1:
			print "OK"
			print conf["to"][mailTo]
		else:
			print "NOPE"
