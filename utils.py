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
	# Remove <> added by some client
	if mailTo[0] == '<':
		length = len(mailTo)
		mailTo = mailTo[1:length-1]
	conf = openYaml(confFile)
	# Check if the mail has a rule, otherwise take the default folder
	folder = conf["to"]["default"]
	for k,v in conf["to"].iteritems():
		if k.find(mailTo) != -1:
			folder = conf["to"][mailTo]
			
	return folder
