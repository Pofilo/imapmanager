from datetime import datetime
import re, quopri, base64

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

# Credits: https://stackoverflow.com/a/43393449
def decodeSubject(subject):
	pattern = re.compile(r'(([^=]*)=\?([^\?]*)\?([BbQq])\?([^\?]*)\?=([^=]*))', re.IGNORECASE)
	data = pattern.findall(subject)
	line = []
	if data:
		for g in data:
			(raw,extra1,encoding,method,string,extra) = g
			extra1 = extra1.replace('\r','').replace('\n','').strip()
			if len(extra1) > 0:
				line.append(extra1)
			if method.lower() == 'q':
				string = quopri.decodestring(string)
				string = string.replace("_"," ").strip()
			if method.lower() == 'b':
				string = base64.b64decode(string)
			line.append(string.decode(encoding,errors='ignore'))
			extra = extra.replace('\r','').replace('\n','').strip()
			if len(extra) > 0:
				line.append(extra)
		subject = "".join(line)

	return subject

