import imaplib
import email
import mailbox

import utils

def connect(username, password, imapServer):
	try:
		# Connect to the mail account
		m = imaplib.IMAP4_SSL(imapServer)
		m.login(username, password)
		utils.log(utils.INFO, 'Successfully logged as "{}"'.format(username))	
	except imaplib.IMAP4.error:
		sys.exit('Login error')
		
	return m

def check(m):
	connectionOk = True
	try:
		m.check()
	except:
		connectionOk = False
	
	return connectionOk

def processMails(conf, m):
	directory = conf[utils.directory]
	# Go into the directory
	m.select(directory)

	# Get the unseen mails of this directory
	typ, data = m.search(None, 'UNSEEN')
	# Counter of the number of mails proccessed
	count = 0
	# Parse the mails
	for num in data[0].split():
		num = int(num)-count
		# See the mail without changing his unread flag
		typ, data = m.fetch(num, '(BODY.PEEK[])')
		#data[0][1] is the raw email
		rawEmail = email.message_from_string(data[0][1])

		folder = ''
		# Check if the mail has a 'subject' rule
		subject = rawEmail[utils.subject]
		if subject:
			folder = utils.getFolder(conf, utils.subject, subject);
			
		# Check if the mail has a 'from' rule
		mailFrom = rawEmail[utils.mfrom]
		if mailFrom:
			mailFrom = utils.cleanAddress(mailFrom.lower())
			if not folder:
				folder = utils.getFolder(conf, utils.mfrom, mailFrom)
			
		# Check if the mail has a 'to' rule
		mailTo = rawEmail[utils.to]
		if mailTo:
			mailTo = utils.cleanAddress(mailTo.lower())
			if not folder:
				folder = utils.getFolder(conf, utils.to, mailTo)
			
		# If we still don't have a rule for the mail, take the default folder
		if not folder:
			folder = utils.getDefaultFolder(conf)
			
		utils.log(utils.INFO, 'GET mail "{}" from "{}" to "{}" to be moved to "{}"'.format(subject, mailFrom, mailTo, folder))			
		# Check if the folder exists
		# TODO
		# boxes = m.list()
		# for box in boxes[1]:
		#	print box
		
		# We copy the mail into the folder
		m.copy(num, folder)
		# We delete the original mail
		typ, data = m.store(num, '+FLAGS', '\\Deleted')
		m.expunge()
		count += 1		
	return data

def logout(m):
	# Close and logout the connection
	m.close()
	m.logout()
	utils.log(utils.INFO, 'Logout success')


