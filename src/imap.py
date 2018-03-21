'''
imap.py: imap's methods used by imap-manager.

imap-manager: Connect and manage your mail account through IMAP.
Copyright (C) 2016-2018 pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.

'''


import imaplib
import email
import mailbox
import sys

import utils
from logger import log, ERROR, WARN, INFO, DEBUG

def connect(hostname, username, password):
	try:
		# Connect to the mail account
		m = imaplib.IMAP4_SSL(hostname)
		m.login(username, password)
		log(INFO, 'Successful connection as "{}"'.format(username))
	except imaplib.IMAP4.error as e:
		log(ERROR, 'Login error: {}'.format(str(e)))
		sys.exit(1)
		
	return m

def check(m):
	connectionOk = True
	try:
		m.check()
	except:
		connectionOk = False
	
	return connectionOk

def processMails(config, m):
	mailbox = config.get(utils.sectionDefault, utils.mailbox)
	# Go into the mailbox
	m.select(mailbox)

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
		subject = rawEmail[utils.imapSubject]
		if subject:
			subject = utils.decodeSubject(subject)
			folder = utils.getFolder(config, utils.imapSubject, subject);
			
		# Check if the mail has a 'from' rule
		mailFrom = rawEmail[utils.imapFrom]
		if mailFrom:
			mailFrom = utils.cleanAddress(mailFrom.lower())
			if not folder:
				folder = utils.getFolder(config, utils.imapFrom, mailFrom)
			
		# Check if the mail has a 'to' rule
		mailTo = rawEmail[utils.imapTo]
		if mailTo:
			mailTo = utils.cleanAddress(mailTo.lower())
			if not folder:
				folder = utils.getFolder(config, utils.imapTo, mailTo)
			
		# If we still don't have a rule for the mail, take the default folder
		if not folder:
			folder = utils.getDefaultFolder(config)
			
		log(INFO, 'GET mail "{}" from "{}" to "{}" to be moved to "{}"'.format(subject.encode('utf8'), mailFrom.encode('utf8'), mailTo.encode('utf8'), folder.encode('utf8')))
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
	log(INFO, 'Successful disconnection')


