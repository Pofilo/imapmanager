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
from typing import List, TypedDict

import requests

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
    SECTION_TELEGRAM_NAME,
    TELEGRAM_TOKEN_NAME,
    TELEGRAM_CHAT_ID_NAME,
    USERNAME_NAME,
)
from imapmanager.utils import decode_subject, extract_and_sanitize_mail_addresses


class MailActions(TypedDict):
    """
    Dict representing all actions to perform after analysing all filters for a given
    category.
    """
    filter_used: bool  # True if a filter matches something
    folder: str
    send_telegram: bool
    mark_as_read: bool

    @classmethod
    def create(
        cls,
        filter_used: bool=False,
        folder: str=None,
        send_telegram: bool=False,
        mark_as_read: bool=False,
    ):
        return MailActions(
            filter_used=filter_used,
            folder=folder,
            send_telegram=send_telegram,
            mark_as_read=mark_as_read,
        )


class Imap:
    """
    Main class of ImapManager.
    Deal with imap connection and process each mail in the inbox.
    """

    def __init__(
        self,
        logger: Logger,
        config: ImapConf,
    ) -> None:
        self.logger = logger
        self._hostname = config.get(HOSTNAME_NAME)
        self._username = config.get(USERNAME_NAME)
        self._default_destination_folder = config.get(IMAP_DEFAULT_FOLDER_NAME)
        self._handler: IMAP4_SSL = None
        self.config = config
        self.running = False

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
            self._handler = IMAP4_SSL(self._hostname, self.config.get(PORT_NAME))
            self._handler.login(self._username, self.config.get(PASSWORD_NAME))
            self.logger.info("Successful connection as username=%s", self._username)
        except Exception as exc:
            # TODO: maybe some retries could be made
            self.panic(f"Failed to login: err={exc}")
            return False

        self._handler.select(self.config.get(MAILBOX_NAME))
        self.running = True
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
            self.running = False
            self.logger.warning(
                "Check connection failed, trying to reconnect: err=%s",
                exc,
            )
            return self._connect()
        return False

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
            typ, data = self._handler.search(None, "UNSEEN")
            if typ != "OK":
                self.panic(
                    f"Fail to search for mails (data={data}), exiting..."
                )
                return
        except Exception as exc:
            self.logger.exception("Failed to search: err=%s", exc)
            return

        # Counter of the number of mails proccessed
        count = 0

        # This for loop is called with index 0 even if there is multiple mails because
        # the mail is supposed to move in the end.
        for num in data[0].split():
            num = str(int(num) - count)

            mail_actions = MailActions.create()

            # Fetch and process mail
            try:
                # See the mail without changing his unread flag
                typ, data = self._handler.fetch(num, "(BODY.PEEK[])")
                if typ != "OK":
                    self.panic(
                        f"Fail to fetch mail with num=\"{num}\" (data={data}), "
                        "exiting..."
                    )
                    return
                # data[0][1] is the raw email
                raw_email = email.message_from_bytes(data[0][1])

                mail_subject = decode_subject(raw_email[IMAP_SUBJECT])

                mail_actions = self._unsafe_process_one_email(raw_email, mail_subject)
            except Exception as exc:
                mail_actions["folder"] = self._default_destination_folder
                self.logger.exception(
                    'Error processing an email, moving it into folder="%s" err=%s',
                    mail_actions["folder"],
                    exc,
                )

            # Check if the folder exists on the server
            if not self._check_folder_exist_on_server(mail_actions["folder"]):
                self.logger.warning(
                    'folder="%s" does not exist on the server, moving the mail '
                    'into the default folder="%s"',
                    mail_actions["folder"],
                    self._default_destination_folder,
                )
                mail_actions["folder"] = self._default_destination_folder
                if not self._check_folder_exist_on_server(mail_actions["folder"]):
                    self.panic(
                        f"default folder=\"{mail_actions['folder']}\" does not exist "
                        "on the server, please fix the configuration, exiting..."
                    )
                    return

            # Mark the mail as read if needed
            if mail_actions["mark_as_read"]:
                typ, data = self._handler.store(num, "+FLAGS", "\Seen")
                if typ != "OK":
                    self.panic(
                        f"Fail to mark mail with subject=\"{mail_subject}\" as read "
                        f"(data=%s), exiting..."
                    )
                    return


            # Copy the mail into the folder
            typ, data = self._handler.copy(num, mail_actions["folder"])
            if typ != "OK":
                self.panic(
                    f"Mail with subject=\"{mail_subject}\" not copied to "
                    f"folder=\"{mail_actions['folder']}\" (data={data}), exiting..."
                )
                return

            # Delete the original mail
            typ, data = self._handler.store(num, "+FLAGS", "\\Deleted")
            if typ != "OK":
                self.panic(
                    f"Fail to delete original mail with subject=\"{mail_subject}\" "
                    f"(data={data}), exiting..."
                )
                return

            self._handler.expunge()

            # Update counter
            count += 1

    def _analyse_filters_for_category(
        self,
        category: str,
        category_name: str,
        params: List[str],
    ) -> MailActions:
        """
        Check if at least one param of params is matching the given category by checking
        all its rules and filters.
        If there is a match, the result is immediately returned.
        The function stop searching after a first match.
        :param      config      the configuration where to get the info from
        :param      category    the configuration section corresponding to the category
                                to check (SUBJECT, FROM, DEST, ...)
        :param      category_name   the name of the category (subject, from, to, cc, ..)
        :param      params      the values to check if one is present in the rule
        :return     result      result of type MailActions
        """
        mail_actions = MailActions.create()

        # Get all rules for the category
        rules = self.config[SECTION_FILTERS_NAME].get(category)
        if rules:
            # A rule has a list of rule composed of rules and filters
            for folder, filters in rules.items():
                # Check every filter in the order
                for filter_ in filters:  # filter variable already exists
                    # For this filter, check if at least one param matches
                    filter_name = list(filter_.keys())[0]
                    for param in params:
                        if filter_name.lower() in param.lower():
                            mail_actions["filter_used"] = True

                            # Filter matches, check its actions
                            if "move" in filter_[filter_name]:
                                mail_actions["folder"] = folder
                            if "telegram" in filter_[filter_name]:
                                mail_actions["send_telegram"] = True
                            if "mark_as_read" in filter_[filter_name]:
                                mail_actions["mark_as_read"] = True

                            self.config.logger.debug(
                                "Got a match for category=%s param=%s folder=%s",
                                category_name,
                                param,
                                mail_actions["folder"],
                            )
                            return mail_actions

        return mail_actions

    def _unsafe_process_one_email(self, raw_email, mail_subject) -> MailActions:
        # pylint: disable=too-many-branches
        mail_actions = MailActions.create()
        rule_used = None
        mail_dest = []

        # Check if the mail has a 'subject' rule
        if mail_subject:
            mail_actions = self._analyse_filters_for_category(
                SECTION_SUBJECT_NAME, IMAP_SUBJECT, [mail_subject]
            )
            if mail_actions["filter_used"]:
                rule_used = IMAP_SUBJECT

        # Check if the mail has a 'from' rule (only if no rules applied yet)
        mail_from = raw_email[IMAP_FROM]
        self.logger.debug('raw field from="%s"', mail_from)
        mail_from = extract_and_sanitize_mail_addresses(mail_from)
        # The list can be empty after <extract_and_sanitize_mail_addresses>
        if mail_from:
            # We don't want to deal with multiple senders
            mail_from = mail_from[0]
            if not rule_used:
                mail_actions = self._analyse_filters_for_category(
                    SECTION_FROM_NAME, IMAP_FROM, [mail_from]
                )
                if mail_actions["filter_used"]:
                    rule_used = IMAP_FROM

        # Check if the mail has a 'to' rule (only if no rules applied yet)
        mail_to = raw_email[IMAP_TO]
        self.logger.debug('raw field to="%s"', mail_to)
        mail_to = extract_and_sanitize_mail_addresses(mail_to)
        # The list can be empty after <extract_and_sanitize_mail_addresses>
        if mail_to:
            mail_dest = mail_dest + mail_to
            if not rule_used:
                mail_actions = self._analyse_filters_for_category(
                    SECTION_DEST_NAME, IMAP_TO, mail_to
                )
                if mail_actions["filter_used"]:
                    rule_used = IMAP_TO

        # Check if the mail has a 'cc' rule (only if no rules applied yet)
        # The values checked for the 'cc' rules are the ones of the 'to' rules
        mail_cc = raw_email[IMAP_CC]
        self.logger.debug('raw field cc="%s"', mail_cc)
        mail_cc = extract_and_sanitize_mail_addresses(mail_cc)
        # The list can be empty after <extract_and_sanitize_mail_addresses>
        if mail_cc:
            mail_dest = mail_dest + mail_cc
            if not rule_used:
                mail_actions = self._analyse_filters_for_category(
                    SECTION_DEST_NAME, IMAP_CC, mail_cc
                )
            if mail_actions["filter_used"]:
                rule_used = IMAP_CC
            
        # If we still don't have a rule for the mail, take the default folder
        if not mail_actions["folder"]:
            self.logger.debug("No rule for the mail, moving it into the default folder")
            mail_actions["folder"] = self._default_destination_folder

        self.logger.info(
            'GET mail subject="%s" from="%s" dest="%s" to be moved into "%s" '
            "(telegram=%s mark_as_read=%s rule=%s)",
            mail_subject,
            mail_from,
            mail_dest,
            mail_actions["folder"],
            mail_actions["send_telegram"],
            mail_actions["mark_as_read"],
            rule_used,
        )

        # Send the telegram notification if needed
        if mail_actions["send_telegram"]:
            self._send_telegram_notification(
                f"GET mail subject=\"{mail_subject}\" from=\"{mail_from}\""
            )

        return mail_actions

    def _send_telegram_notification(self, message: str = None) -> None:
        """
        Send msg is telegram section is defined in the configuration.
        """
        if self.config.get(SECTION_TELEGRAM_NAME, {}):
            token = self.config[SECTION_TELEGRAM_NAME][TELEGRAM_TOKEN_NAME]
            chat_id = self.config[SECTION_TELEGRAM_NAME][TELEGRAM_CHAT_ID_NAME]
            try:
                url = (
                    f"https://api.telegram.org/bot{token}/sendMessage?"
                    f"chat_id={chat_id}&text={message}"
                )
                # TODO: this produces debug logs
                resp = requests.get(url, timeout=5)
                if resp.status_code != 200:
                    self.logger.warning(
                        "Failed to send telegram message, status_code=%s err=%s",
                        resp.status_code,
                        resp.text,
                    )
            except Exception as exc:
                self.logger.exception("Failed to send telegram message: err=%s", exc)

    def panic(self, msg: str) -> None:
        self.running = False

        self.logger.critical(msg)
        
        # If telegram is defined in the configuration, send a notification
        self._send_telegram_notification(msg)
        
        self.logout()

    def logout(self) -> None:
        """
        Logout and close the mail handler.
        """
        # Close and logout the connection
        if self._handler:
            try:
                self._handler.close()
                self._handler.logout()
                self._handler = None
                self.logger.info("Successful disconnection")
            except Exception as exc:
                self.logger.exception("Failed to close/logout: err=%s", exc)
