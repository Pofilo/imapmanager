'''
imap.py: imap's methods used by imap-manager.

imap-manager: Connect and manage your mail account through IMAP.
Copyright (C) 2016-2020 pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.

'''


import imaplib
import email
import mailbox
import sys
import logging

import utils

logger = logging.getLogger('imapmanager')

def __get_folder_from_rule(config, rule, param):
    """
    Return, if exists, the folder corresponding to the given rule.
    :param      config      the configuration where to get the info from
    :param      rule        the configuration section corresponding to the rule to check (subject, from, to, ...)
    :param      param       the value to check if present in the rule
    :return     folder      the folder name, an empty string otherwise
    """
    folder = ''
    # Check if the mail has a rule
    for argument, value in list(config.items(rule)):
        # Remove the quotes
        argument = argument[1:-1]
        if argument.lower() in param.lower():
            folder = value
            break

    return folder

def __get_default_destination_folder(config):
    """
    This function returns the IMAP default destination folder from configuration.
    It corresponds to the folder used if no rule matches the mail.
    :param      config      the configuration
    :return:                the IMAP default folder
    """
    # Get the default folder in the config file
    return config.get(SECTION_GENERAL_NAME, IMAP_DEFAULT_FOLDER_NAME)

def connect(hostname, port, username, password):
    """
    This function create and connect a mail handler.
    :param      hostname    the hostname of the mail server
    :param      port        the port of the mail server
    :param      username    the name of the user
    :param      password    the password of the user
    :return                 the mail handler
    """
    try:
        # Connect to the mail account
        mail_handler = imaplib.IMAP4_SSL(hostname, port)
        mail_handler.login(username, password)
        logger.info('Successful connection as "{}"'.format(username))
    except imaplib.IMAP4.error as error:
        logger.critical('Login error: {}'.format(str(error)))
        sys.exit(1)
    except BaseException as error:
        logger.critical('Login error: {}'.format(str(error)))
        sys.exit(1)

    return mail_handler

def check_connection(mail_handler):
    """
    This function checks that the mail handler is still successfully connected.
    :param      mail_handler    the handler to check
    :return                     True if connection OK, False otherwise
    """
    connection_ok = True
    try:
        mail_handler.check()
    except:
        connection_ok = False

    return connection_ok

def process_mails(config, mail_handler):
    """
    Process all mails mark as UNREAD in the mailbox.
    :param      config          the configuration
    :param      mail_handler    the handler of the mail
    """
    mailbox = config.get(utils.SECTION_GENERAL_NAME, utils.MAILBOX_NAME)
    # Go into the mailbox
    mail_handler.select(mailbox)

    # Get the unseen mails of this directory
    typ, data = mail_handler.search(None, 'UNSEEN')
    # Counter of the number of mails proccessed
    count = 0
    # Parse the mails
    # TODO
    # This for loop is called individually even if there is multiple mails
    # Check the good usage to parse mails
    for num in data[0].split():
        num = str(int(num)-count)
        try:
            # See the mail without changing his unread flag
            typ, data = mail_handler.fetch(num, '(BODY.PEEK[])')
            #data[0][1] is the raw email
            raw_email = email.message_from_bytes(data[0][1])

            folder = ''
            # Check if the mail has a 'subject' rule
            subject = raw_email[utils.IMAP_SUBJECT]
            if subject:
                subject = utils.decode_subject(subject)
                folder = __get_folder_from_rule(config, utils.SECTION_SUBJECT_NAME, subject)

            # Check if the mail has a 'from' rule
            mail_from = raw_email[utils.IMAP_FROM]
            if mail_from:
                mail_from = utils.clean_mail_address(mail_from.lower())
                if not folder:
                    folder = __get_folder_from_rule(config, utils.SECTION_FROM_NAME, mail_from)

            # Check if the mail has a 'to' rule
            mail_to = raw_email[utils.IMAP_TO]
            if mail_to:
                mail_to = utils.clean_mail_address(mail_to.lower())
                if not folder:
                    folder = __get_folder_from_rule(config, utils.SECTION_TO_NAME, mail_to)

            # If we still don't have a rule for the mail, take the default folder
            if not folder:
                folder = __get_default_destination_folder(config)

            logger.info('GET mail "{}" from "{}" to "{}" to be moved to "{}"'.format(subject, mail_from, mail_to, folder))

            # Check if the folder exists on the server
            # TODO
            # boxes = m.list()
            # for box in boxes[1]:
            #    print box
        except BaseException as e:
            folder = __get_default_folder(config)
            logger.error('Error processing an email, moving it into "{}", error: "{}"'.format(folder, str(e)))

        # We copy the mail into the folder
        mail_handler.copy(num, folder)
        # We delete the original mail
        typ, data = mail_handler.store(num, '+FLAGS', '\\Deleted')
        mail_handler.expunge()
        count += 1
    return

def logout(mail_handler):
    """
    Logout and close the mail handler.
    :param      mail_handler        the handler to logout and close
    """
    # Close and logout the connection
    mail_handler.close()
    mail_handler.logout()
    logger.info('Successful disconnection')

