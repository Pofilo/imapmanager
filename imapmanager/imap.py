"""
imap.py: imap's methods used by imapmanager.

imapmanager: Connect and manage your mail account through IMAP.
Copyright (C) pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms
of the GNU General Public License as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANYWARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>.
"""


import imaplib
import email
import sys
import logging
import traceback

from imapmanager import utils

logger = logging.getLogger("imapmanager")


# TODO: this function is not understandable
def _check_rule_for_params(config, rule, rule_name, params):
    """
    Check if one over each params is matching the given rule.
    If there is a match, the folder and the param are returned.
    The function stop searching after a first match.
    :param      config      the configuration where to get the info from
    :param      rule        the configuration section corresponding to the rule to check
                            (SUBJECT, FROM, DEST, ...)
    :param      rule_name   the name of the rule (subject, from, to, cc, ...)
    :param      params      the values to check if one is present in the rule
    :return     folder      the folder name, an empty string otherwise
    """
    folder = ""
    # Check if the mail has a rule
    for argument, value in list(config.items(rule)):
        # Remove the quotes
        argument = argument[1:-1]
        for param in params:
            if argument.lower() in param.lower():
                folder = value
                logger.debug(
                    "Got a match for rule=%s param=%s folder=%s",
                    rule_name,
                    param,
                    folder,
                )
                return folder

    return folder


def _get_default_destination_folder(config):
    """
    This function returns the IMAP default destination folder from configuration.
    It corresponds to the folder used if no rule matches the mail.
    :param      config      the configuration
    :return:                the IMAP default folder
    """
    # Get the default folder in the config file
    return config.get(utils.SECTION_GENERAL_NAME, utils.IMAP_DEFAULT_FOLDER_NAME)


def _check_folder_exist_on_server(mail_handler, folder_name):
    """
    This function check that the given folder exists on the server.
    Folder on the server looks like:
        (\HasNoChildren) "." "INBOX.spam"  # noqa: W605
        (\HasNoChildren) "." INBOX.spam  # noqa: W605
    :param      mail_handler        the handler of the mail server
    :param      folder_name         the name of the folder to check
    :return     does_folder_exist   True if the folder exists, False otherwise.
    """
    does_folder_exist = True
    list_folders = mail_handler.list()

    if not any(
        folder_name in folder_server.decode(utils.ENCODING).replace('"', "")
        for folder_server in list_folders[1]
    ):
        does_folder_exist = False

    return does_folder_exist


def connect(hostname, port, username, password, mailbox):
    """
    This function create and connect a mail handler.
    :param      hostname    the hostname of the mail server
    :param      port        the port of the mail server
    :param      username    the name of the user
    :param      password    the password of the user
    :param      mailbox     the name of the folder where imapmanager will process
                            unread mails
    :return                 the mail handler
    """
    try:
        # Connect to the mail account
        mail_handler = imaplib.IMAP4_SSL(hostname, port)
        mail_handler.login(username, password)
        logger.info("Successful connection as username=%s", username)
    except (imaplib.IMAP4.error, BaseException) as exc:
        logger.exception("Failed to login: err=%s", exc)
        sys.exit(1)

    mail_handler.select(mailbox)

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
    except (imaplib.IMAP4.error, BaseException) as exc:
        logger.exception("Failed to check connection: err=%s", exc)
        connection_ok = False

    return connection_ok


def process_mails(config, mail_handler):
    """
    Process all mails mark as UNREAD in the mailbox.
    :param      config          the configuration
    :param      mail_handler    the handler of the mail
    """
    mailbox = config.get(utils.SECTION_GENERAL_NAME, utils.MAILBOX_NAME)

    try:
        # Go into the mailbox
        mail_handler.select(mailbox)
    except (imaplib.IMAP4.error, BaseException) as exc:
        logger.exception("Failed to select: err=%s", exc)
        return

    try:
        # Get the unseen mails of this directory
        typ, data = mail_handler.search(None, "UNSEEN")
    except (imaplib.IMAP4.error, BaseException) as exc:
        logger.exception("Failed to search: err=%s", exc)
        return

    # Counter of the number of mails proccessed
    count = 0

    # Parse the mails
    # TODO
    # This for loop is called individually even if there is multiple mails
    # Check the good usage to parse mails
    for num in data[0].split():
        num = str(int(num) - count)
        # The name of the folder where the current mail will be moved
        folder_name = ""

        # This try-except seems to only be usefull if the message_from_bytes() fails
        try:
            # See the mail without changing his unread flag
            typ, data = mail_handler.fetch(num, "(BODY.PEEK[])")
            # data[0][1] is the raw email
            raw_email = email.message_from_bytes(data[0][1])

            mail_dest = []
            # Check if the mail has a 'subject' rule
            subject = raw_email[utils.IMAP_SUBJECT]
            if subject:
                subject = utils.decode_subject(subject)
                folder_name = _check_rule_for_params(
                    config, utils.SECTION_SUBJECT_NAME, utils.IMAP_SUBJECT, [subject]
                )

            # Check if the mail has a 'from' rule (only if no rules applied yet)
            mail_from = raw_email[utils.IMAP_FROM]
            logger.debug("field from=%s", mail_from)
            mail_from = utils.extract_and_sanitize_mail_addresses(mail_from)
            if mail_from:
                # We don't want to deal with multiple senders
                mail_from = mail_from[0]
                if not folder_name:
                    folder_name = _check_rule_for_params(
                        config, utils.SECTION_FROM_NAME, utils.IMAP_FROM, [mail_from]
                    )

            # Check if the mail has a 'to' rule (only if no rules applied yet)
            mail_to = raw_email[utils.IMAP_TO]
            logger.debug("field to=%s", mail_to)
            mail_to = utils.extract_and_sanitize_mail_addresses(mail_to)
            # Init mail_dest with first mail found
            # (init in case a previous rule applied)
            if mail_to:
                # Init mail_dest with first mail found
                # (init in case a previous rule applied)
                mail_dest = mail_dest + mail_to
                if not folder_name:
                    folder_name = _check_rule_for_params(
                        config, utils.SECTION_DEST_NAME, utils.IMAP_TO, mail_to
                    )

            # Check if the mail has a 'cc' rule (only if no rules applied yet)
            # The values checked for the 'cc' rules are the ones of the 'to' rules
            mail_cc = raw_email[utils.IMAP_CC]
            logger.debug("field cc=%s", mail_cc)
            if mail_cc:
                mail_cc = utils.extract_and_sanitize_mail_addresses(mail_cc)
                # The list can be empty after <extract_and_sanitize_mail_addresses>
                if mail_cc:
                    mail_dest = mail_dest + mail_cc
                    if not folder_name:
                        folder_name = _check_rule_for_params(
                            config, utils.SECTION_DEST_NAME, utils.IMAP_CC, mail_cc
                        )

            # If we still don't have a rule for the mail, take the default folder
            if not folder_name:
                logger.debug("No rule for the mail, moving it into the default folder")
                folder_name = _get_default_destination_folder(config)

            logger.info(
                "GET mail subject=%s from=%s dest=%s to be moved into folder=%s",
                subject,
                mail_from,
                mail_dest,
                folder_name,
            )
        except BaseException as exc:
            folder_name = _get_default_destination_folder(config)
            logger.exception(
                "Error processing an email, moving it into folder=%s err=%s",
                folder_name,
                exc,
            )

        # Check if the folder exists on the server
        if not _check_folder_exist_on_server(mail_handler, folder_name):
            logger.warning(
                "folder=%s does not exist on the server, moving the mail "
                "into the default folder=%s",
                folder_name,
                _get_default_destination_folder(config),
            )
            folder_name = _get_default_destination_folder(config)
            if not _check_folder_exist_on_server(mail_handler, folder_name):
                logger.critical(
                    "default folder=%s does not exist on the server, "
                    "please fix the configuration, exiting..",
                    folder_name,
                )
                sys.exit(1)

        # We copy the mail into the folder
        result = mail_handler.copy(num, folder_name)
        if result[0] != "OK":
            logger.critical(
                "Mail with subject=%s not copied to folder=%s, exiting...",
                subject,
                folder_name,
            )
            sys.exit(1)
        # We delete the original mail
        typ, data = mail_handler.store(num, "+FLAGS", "\\Deleted")
        mail_handler.expunge()

        # Update counter
        count += 1
    return


def logout(mail_handler):
    """
    Logout and close the mail handler.
    :param      mail_handler        the handler to logout and close
    """
    # Close and logout the connection
    try:
        mail_handler.close()
        mail_handler.logout()
        logger.info("Successful disconnection")
    except (imaplib.IMAP4.error, BaseException) as exc:
        logger.exception("Failed to close/logout: err=%s", exc)
