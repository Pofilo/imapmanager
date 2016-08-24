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
		# print "Successfully logged as %r" % username

	except imaplib.IMAP4.error:
		sys.exit("Error during the execution of the script")

	return mail

def processMails(confFile, mail):
	
	directory = getParameter(confFile, "directory")
	
	# Go into the <directory> directory
	mail.select(directory)
	# Get the unseen mails of this directory
	typ, data = mail.search(None, 'UNSEEN')

	# Counter of the number of mails proccessed
	count = 0
	# Parse the mails
	for num in data[0].split():
		num = int(num)-count
		# See the mail without changing his unread flag
		typ, data = mail.fetch(num, '(BODY.PEEK[])')
		mailTo = str(email.header.make_header(email.header.decode_header(email.message_from_string(data[0][1].decode('utf-8'))['To'])))
		# Get the name of the folder for this mail
		folder = getFolder(confFile, mailTo)
		# We copy the mail into the folder
		mail.copy(num, folder)
		# We delete the original mail
		mov, data = mail.store(num, '+FLAGS', '\\Deleted')
		mail.expunge()
		count += 1
	return data

def logout(mail):
	# Close and logout the connection
	mail.close()
	mail.logout()


