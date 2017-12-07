from datetime import datetime

username = 'username'
password = 'password'
imapServer = 'imapServer'
directory = 'directory'
sleepDuration = 'sleepDuration'
directory = 'directory'
subject = 'subject'
mfrom = 'from'
to = 'to'
default = 'default'
defaultConfigPath = '../config/config.yaml'

# LOGS
ERROR = 'ERROR'
WARN = 'WARN'
INFO = 'INFO'
DEBUG = 'DEBUG'

def getFolder(conf, rule, param):
	folder = ''
	# Check if the mail has a rule
	for argument, value in conf[rule].iteritems():
		if argument in param:
			folder = value
			break

	return folder
	
def getDefaultFolder(conf):
	# Get the default folder in the conf file
	return conf[default]
	
def cleanAddress(address):
	# Remove <> added by some client and only get the content inside
	if '<' in address:
		address = address.split('<')[1]
		if '>' in address:
			address = address.split('>')[0]
		
	return address

def log(level, message):
	print '{} ({}): {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), level, message)

