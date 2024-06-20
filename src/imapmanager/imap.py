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

import email
from imaplib import IMAP4_SSL
from logging import Logger
import sys
from typing import List

from imapmanager.conf import ImapConf
from imapmanager.constants import (
    ENCODING,
    HOSTNAME_NAME,
    IMAP_CC,
    IMAP_DEFAULT_FOLDER_NAME,
    IMAP_FROM,
    IMAP_SUBJECT,
    IMAP_TO,
    MAILBOX_NAME,
    PASSWORD_NAME,
    PORT_NAME,
    SECTION_FILTERS_NAME,
    SECTION_FROM_NAME,
    SECTION_DEST_NAME,
    SECTION_SUBJECT_NAME,
    USERNAME_NAME,
)
from imapmanager.utils import decode_subject, extract_and_sanitize_mail_addresses


# TODO: this function is not understandable
def _analyse_filters_for_category(
    config: ImapConf,
    category: str,
    category_name: str,
    params: List[str],
):
    """
    Check if one over each params is matching the given category.
    If there is a match, the folder and True are returned.
    The function stop searching after a first match.
    :param      config      the configuration where to get the info from
    :param      category        the configuration section corresponding to the category
                                to check (SUBJECT, FROM, DEST, ...)
    :param      category_name   the name of the category (subject, from, to, cc, ...)
    :param      params      the values to check if one is present in the rule
    :return     folder      the folder name, an empty string otherwise
    :return     used        True if the rule was matching something, False otherwise
    """
    rules = config[SECTION_FILTERS_NAME].get(category)
    if rules:
        for folder, filters in rules.items():
            # filters are all the values in conf to check
            for filter in filters:
                for param in params:
                    if filter.lower() in param.lower():
                        config.logger.debug(
                            "Got a match for category=%s param=%s folder=%s",
                            category_name,
                            param,
                            folder,
                        )
                        return folder, True

    return None, False


class Imap:
    def __init__(
        self,
        logger: Logger,
        config: ImapConf,
    ) -> None:
        self.logger = logger
        self._hostname = config.get(HOSTNAME_NAME)
        self._port = config.get(PORT_NAME)
        self._username = config.get(USERNAME_NAME)
        self._password = config.get(PASSWORD_NAME)
        self._mailbox = config.get(MAILBOX_NAME)
        self._default_destination_folder = config.get(IMAP_DEFAULT_FOLDER_NAME)
        self._handler: IMAP4_SSL = None
        self.config = config

        self._connect()

        logger.info(
            "imapmanager initialized with on %s with %s", self._hostname, self._username
        )

    def _connect(self) -> bool:
        """
        Connect and select the mailbox.
        # TODO: do not exit but manage errors properly.
        :return     True if the connection is successful, exit otherwise.
        """
        try:
            # Connect to the mail account
            self._handler = IMAP4_SSL(self._hostname, self._port)
            self._handler.login(self._username, self._password)
            self.logger.info("Successful connection as username=%s", self._username)
        except Exception as exc:
            self.logger.exception("Failed to login: err=%s", exc)
            sys.exit(1)

        self._handler.select(self._mailbox)
        return True

    def _maybe_reconnect(self) -> bool:
        """
        If handler is not connected yet or disconnected, reconnect it.
        :return     True if the connection is successful, False otherwise.
        """
        try:
            if self._handler.check():
                return True
        except Exception as exc:
            self.logger.warning(
                "Check connection failed, trying to reconnect: err=%s",
                exc,
            )
            return self._connect()

    def _check_folder_exist_on_server(self, folder_name) -> bool:
        """
        This function check that the given folder exists on the server.
        Folder on the server looks like (with a baskslash removed):
            (\\HasNoChildren) "." "INBOX.spam"
            (\\HasNoChildren) "." INBOX.spam
        :param      folder_name         the name of the folder to check
        :return                         True if the folder exists, False otherwise.
        """
        list_folders = self._handler.list()

        return any(
            folder_name in folder_server.decode(ENCODING).replace('"', "")
            for folder_server in list_folders[1]
        )

    def process_mails(self) -> None:
        """
        Process all mails mark as UNREAD in the mailbox.
        """
        # First, check if the connection is still alive
        if not self._maybe_reconnect():
            # Connection failure, try again later...
            return

        mailbox = self.config.get(MAILBOX_NAME)

        try:
            # Go into the mailbox
            self._handler.select(mailbox)
        except Exception as exc:
            self.logger.exception("Failed to select: err=%s", exc)
            return

        try:
            # Get the unseen mails of this directory
            _typ, data = self._handler.search(None, "UNSEEN")
        except Exception as exc:
            self.logger.exception("Failed to search: err=%s", exc)
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
            folder_name = None

            # Fetch and process mail
            try:
                # See the mail without changing his unread flag
                _typ, data = self._handler.fetch(num, "(BODY.PEEK[])")
                # data[0][1] is the raw email
                raw_email = email.message_from_bytes(data[0][1])

                mail_subject = raw_email[IMAP_SUBJECT]
                if mail_subject:
                    mail_subject = decode_subject(mail_subject)

                folder_name = self._unsafe_process_one_email(raw_email, mail_subject)
            except Exception as exc:
                folder_name = self._default_destination_folder
                self.logger.exception(
                    'Error processing an email, moving it into folder="%s" err=%s',
                    folder_name,
                    exc,
                )

            # Check if the folder exists on the server
            if not self._check_folder_exist_on_server(folder_name):
                self.logger.warning(
                    'folder="%s" does not exist on the server, moving the mail '
                    'into the default folder="%s"',
                    folder_name,
                    self._default_destination_folder,
                )
                folder_name = self._default_destination_folder
                if not self._check_folder_exist_on_server(folder_name):
                    self.logger.critical(
                        'default folder="%s" does not exist on the server, '
                        "please fix the configuration, exiting..",
                        folder_name,
                    )
                    sys.exit(1)

            # Copy the mail into the folder
            result = self._handler.copy(num, folder_name)
            if result[0] != "OK":
                self.logger.critical(
                    'Mail with subject="%s" not copied to folder="%s", exiting...',
                    mail_subject,
                    folder_name,
                )
                sys.exit(1)
            # Delete the original mail
            _typ, data = self._handler.store(num, "+FLAGS", "\\Deleted")
            self._handler.expunge()

            # Update counter
            count += 1

    def _unsafe_process_one_email(self, raw_email, mail_subject):
        folder_name = None
        rule_used = None
        mail_dest = []

        # Check if the mail has a 'subject' rule
        if mail_subject:
            mail_subject = decode_subject(mail_subject)
            folder_name, used = _analyse_filters_for_category(
                self.config, SECTION_SUBJECT_NAME, IMAP_SUBJECT, [mail_subject]
            )
            if used:
                rule_used = IMAP_SUBJECT

        # Check if the mail has a 'from' rule (only if no rules applied yet)
        mail_from = raw_email[IMAP_FROM]
        self.logger.debug('field from="%s"', mail_from)
        mail_from = extract_and_sanitize_mail_addresses(mail_from)
        if mail_from:
            # We don't want to deal with multiple senders
            mail_from = mail_from[0]
            if not folder_name:
                folder_name, used = _analyse_filters_for_category(
                    self.config, SECTION_FROM_NAME, IMAP_FROM, [mail_from]
                )
                if used:
                    rule_used = IMAP_FROM

        # Check if the mail has a 'to' rule (only if no rules applied yet)
        mail_to = raw_email[IMAP_TO]
        self.logger.debug('field to="%s"', mail_to)
        mail_to = extract_and_sanitize_mail_addresses(mail_to)
        # Init mail_dest with first mail found
        # (init in case a previous rule applied)
        if mail_to:
            # Init mail_dest with first mail found
            # (init in case a previous rule applied)
            mail_dest = mail_dest + mail_to
            if not folder_name:
                folder_name, used = _analyse_filters_for_category(
                    self.config, SECTION_DEST_NAME, IMAP_TO, mail_to
                )
                if used:
                    rule_used = IMAP_TO

        # Check if the mail has a 'cc' rule (only if no rules applied yet)
        # The values checked for the 'cc' rules are the ones of the 'to' rules
        mail_cc = raw_email[IMAP_CC]
        self.logger.debug('field cc="%s"', mail_cc)
        if mail_cc:
            mail_cc = extract_and_sanitize_mail_addresses(mail_cc)
            # The list can be empty after <extract_and_sanitize_mail_addresses>
            if mail_cc:
                mail_dest = mail_dest + mail_cc
                if not folder_name:
                    folder_name, used = _analyse_filters_for_category(
                        self.config, SECTION_DEST_NAME, IMAP_CC, mail_cc
                    )
                if used:
                    rule_used = IMAP_CC

        # If we still don't have a rule for the mail, take the default folder
        if not folder_name:
            self.logger.debug("No rule for the mail, moving it into the default folder")
            folder_name = self._default_destination_folder

        self.logger.info(
            'GET mail subject="%s" from="%s" dest="%s" to be moved into "%s" '
            "(rule=%s)",
            mail_subject,
            mail_from,
            mail_dest,
            folder_name,
            rule_used,
        )
        return folder_name

    def logout(self) -> None:
        """
        Logout and close the mail handler.
        """
        # Close and logout the connection
        try:
            self._handler.close()
            self._handler.logout()
            self.logger.info("Successful disconnection")
        except Exception as exc:
            self.logger.exception("Failed to close/logout: err=%s", exc)
