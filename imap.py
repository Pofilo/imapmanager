import imaplib
import email
import mailbox

from utils import getParameter
from utils import getFolder

def connect(confFile):

	username = getParameter(confFile, "username")
	password = getParameter(confFile, "password")
	imapServer = getParameter(confFile, "imapServer")

	# Connect to the mail account
	mail = imaplib.IMAP4_SSL(imapServer)

	try:
		mail.login(username, password)
		print "Successfully logged as %r" % username

	except imaplib.IMAP4.error:
		sys.exit("Error during the execution of the script")

	return mail

def parseMail(confFile, mail):
	
	directory = getParameter(confFile, "directory")
	
	# Go into the <directory> directory
	mail.select(directory)
	# Get the unseen mails of this directory
	typ, data = mail.search(None, 'UNSEEN')

	# Parse the mails
	for num in data[0].split():
		# See the mail without changing his unread flag
		typ, data = mail.fetch(num, '(BODY.PEEK[])')
		print 'Message %s\n%s\n' % (num, data[0][1])

		mailTo = str(email.header.make_header(email.header.decode_header(email.message_from_string(data[0][1].decode('utf-8'))['To'])))
		print '---> To: %s' % (mailTo)
		getFolder(confFile, mailTo)

	return data

def logout(mail):
	# Close and logout the connection
	mail.close()
	mail.logout()


