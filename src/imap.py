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
from logger import Logger, FATAL, ERROR, WARN, INFO, DEBUG

my_logger = Logger()

def connect(hostname, port, username, password):
	try:
		# Connect to the mail account
		m = imaplib.IMAP4_SSL(hostname, port)
		m.login(username, password)
		my_logger.log(INFO, 'Successful connection as "{}"'.format(username))
	except imaplib.IMAP4.error as e:
		my_logger.log(ERROR, 'Login error: {}'.format(str(e)))
		sys.exit(1)
	except BaseException as e:
		my_logger.log(ERROR, 'Login error: {}'.format(str(e)))
		sys.exit(1)

	return m

def check(m):
	connection_ok = True
	try:
		m.check()
	except:
		connection_ok = False

	return connection_ok

def process_mails(config, m):
	mailbox = config.get(utils.SECTION_GENERAL_NAME, utils.MAILBOX_NAME)
	# Go into the mailbox
	m.select(mailbox)

	# Get the unseen mails of this directory
	typ, data = m.search(None, 'UNSEEN')
	# Counter of the number of mails proccessed
	count = 0
	# Parse the mails
	for num in data[0].split():
		try:
			num = int(num)-count
			# See the mail without changing his unread flag
			typ, data = m.fetch(num, '(BODY.PEEK[])')
			#data[0][1] is the raw email
			raw_email = email.message_from_string(data[0][1])

			folder = ''
			# Check if the mail has a 'subject' rule
			subject = raw_email[utils.IMAP_SUBJECT]
			if subject:
				subject = utils.decode_subject(subject)
				folder = utils.get_folder(config, utils.SECTION_SUBJECT_NAME, subject)

			# Check if the mail has a 'from' rule
			mail_from = raw_email[utils.IMAP_FROM]
			if mail_from:
				mail_from = utils.clean_address(mail_from.lower())
				if not folder:
					folder = utils.get_folder(config, utils.SECTION_FROM_NAME, mail_from)

			# Check if the mail has a 'to' rule
			mail_to = raw_email[utils.IMAP_TO]
			if mail_to:
				mail_to = utils.clean_address(mail_to.lower())
				if not folder:
					folder = utils.get_folder(config, utils.SECTION_TO_NAME, mail_to)

			# If we still don't have a rule for the mail, take the default folder
			if not folder:
				folder = utils.get_default_folder(config)

			my_logger.log(INFO, 'GET mail "{}" from "{}" to "{}" to be moved to "{}"'.format(
				subject, mail_from, mail_to, folder))
				
			# Check if the folder exists
			# TODO
			# boxes = m.list()
			# for box in boxes[1]:
			#	print box
		except BaseException as e:
			folder = utils.get_default_folder(config)
			my_logger.log(ERROR, 'Error processing an email, moving it into "{}", error: "{}"'.format(folder, str(e)))

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
	my_logger.log(INFO, 'Successful disconnection')
