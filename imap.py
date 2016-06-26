import imaplib
import sys
import yaml

def connect(confFile):
	with open(confFile, 'r') as f:
		conf = yaml.load(f)
		
	username = conf["username"]
	password = conf["password"]
	imapServer = conf["imapServer"]

	mail = imaplib.IMAP4_SSL(imapServer)
	try:
		mail.login(username, password)
		print "Successfully logged as %r" % username
	except imaplib.IMAP4.error:
		sys.exit("Log in failed")

	return mail
