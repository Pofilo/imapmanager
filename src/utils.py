'''
utils.py: useful and general methods for imap-manager.

imap-manager: Connect and manage your mail account through IMAP.
Copyright (C) 2016-2018 pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.

'''


import re, quopri, base64

sectionDefault = 'default'
hostname = 'imap_hostname'
username = 'imap_username'
password = 'imap_password'
mailbox = 'imap_mailbox'
pollingInterval = 'polling_interval'

imapSubject = 'subject'
imapFrom = 'from'
imapTo = 'to'
imapDefaultFolder = 'default_folder'
defaultConfigPath = '../config/imap-manager.conf'

def getFolder(config, rule, param):
	folder = ''
	# Check if the mail has a rule
	for argument, value in list(config.items(rule)):
		# Remove the quotes
		argument = argument[1:-1]
		if argument.lower() in param.lower():
			folder = value
			break

	return folder

def getDefaultFolder(config):
	# Get the default folder in the config file
	return config.get(sectionDefault, imapDefaultFolder)

def cleanAddress(address):
	# Remove <> added by some client and only get the content inside
	if '<' in address:
		address = address.split('<')[1]
		if '>' in address:
			address = address.split('>')[0]

	return address

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
