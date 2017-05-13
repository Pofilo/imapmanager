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

def getFolderTo(confFile, mailTo):
	folder = ""
	# Remove <> added by some client
	if mailTo[0] == '<':
		length = len(mailTo)
		mailTo = mailTo[1:length-1]
	conf = openYaml(confFile)
	# Check if the mail has a rule
	for k,v in conf["to"].iteritems():
		if mailTo.find(k) != -1:
			folder = conf["to"][k]

	return folder
	
def getFolderSubject(confFile, subject):
	folder = ""
	conf = openYaml(confFile)
	# Check if the mail has a spam rule
	for k,v in conf["subject"].iteritems():
		if subject.find(k) != -1:
			folder = conf["subject"][k]

	return folder

def getDefaultFolder(confFile):
	# Open the conf file
	conf = openYaml(confFile)
	# Get the default folder in the conf file
	return conf["to"]["default"]

	