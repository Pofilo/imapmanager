"""
imap.py: imap's methods used by imapmanager.

imapmanager: Connect and manage your mail account through IMAP.
Copyright (C) pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms
of the GNU General Public License as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import email
from dataclasses import dataclass, field
from email import policy
from imaplib import IMAP4, IMAP4_SSL
from ssl import SSLError, create_default_context
from typing import TYPE_CHECKING

from imapmanager.constants import (
    DEFAULT_WEIGHT,
    ENCODING,
    FILTER_ACTION_MARK_AS_READ_NAME,
    FILTER_ACTION_MOVE_NAME,
    FILTER_ACTIONS_NAME,
    FILTER_PATTERN_NAME,
    FILTER_WEIGHT_NAME,
    HEARTBEAT_GRACE,
    HOSTNAME_NAME,
    IMAP_BODY,
    IMAP_CC,
    IMAP_DEFAULT_FOLDER_NAME,
    IMAP_FROM,
    IMAP_SUBJECT,
    IMAP_TO,
    MAILBOX_NAME,
    NOTIFIERS,
    PASSWORD_NAME,
    PORT_NAME,
    SECTION_BODY_NAME,
    SECTION_DEST_NAME,
    SECTION_FILTERS_NAME,
    SECTION_FROM_NAME,
    SECTION_SUBJECT_NAME,
    USERNAME_NAME,
    WEIGHT_NAME,
)
from imapmanager.notifiers import Notifiers
from imapmanager.utils import (
    decode_subject,
    extract_and_sanitize_mail_addresses,
    normalize_patterns,
)

if TYPE_CHECKING:
    from email.message import EmailMessage
    from logging import Logger
    from threading import Event

    from imapmanager.conf import ImapConf
    from imapmanager.heartbeat import Heartbeat

# Reconnection backoff on transient connection/SSL errors.
RECONNECT_INITIAL_DELAY = 5  # seconds
RECONNECT_MAX_DELAY = 300  # seconds (cap)
RECONNECT_MULTIPLIER = 2
RECONNECT_MAX_AUTH_ATTEMPTS = 10  # IMAP4.error (login) tolerated before giving up

SOCKET_TIMEOUT = 60

# Socket abort / TLS handshake / network errors -> transient errors.
# A socket timeout raises TimeoutError, a subclass of OSError, so it lands here too.
TRANSIENT_ERRORS = (IMAP4.abort, SSLError, OSError)


@dataclass
class MailAction:
    """
    Represent what to perform on the mail.
    """

    rule_name: str | None = None  # Name of the rule (None for no rule)
    folder: str | None = None
    notifiers: tuple[str, ...] = ()  # Notifiers to send a notification to
    mark_as_read: bool = False
    weight: int = DEFAULT_WEIGHT  # Higher wins when multiple rules match
    mail_from: str | None = None
    mail_dest: list[str] = field(default_factory=list)


class MailActions:
    """
    List of every <MailAction> that matched a given mail.
    Provides <get_best_action> for the rule with the best match.
    """

    def __init__(self, logger: Logger) -> None:
        self.logger = logger
        self._actions: list[MailAction] = []

    def append(self, action: MailAction) -> None:
        """
        Add a matching MailAction if it was resolved.
        """
        if action.rule_name is not None:
            self._actions.append(action)

    def get_best_action(self) -> MailAction:
        """
        Return the <MailAction> for the highest-weight match.
        Returns default MailAction when no rule matched.

        Exactly-one-rule semantics: only the single highest-weight match is
        returned; the actions of the other matches are discarded (never merged).
        Ties keep insertion order (the first match evaluated wins).
        """
        if not self._actions:
            self.logger.debug("No matches, return default")
            return MailAction()

        # stable sort (entries with same weight keep their insertion order in the list)
        sorted_actions = sorted(self._actions, key=lambda m: m.weight, reverse=True)
        best_action = sorted_actions[0]
        self.logger.debug(
            "Best matching rule: rule=%s weight=%d (evaluated %d matches)",
            best_action.rule_name,
            best_action.weight,
            len(sorted_actions),
        )
        return best_action


# TODO(pofilo): reduce complexity
# 028
# ruff: noqa: C901  (complex-structure)
# ruff: noqa: PLR0911 (too-many-return-statements)
# ruff: noqa: PLR0912 (too-many-branches)
# ruff: noqa: PLR0915 (too-many-statements)
class Imap:
    """
    Main class of ImapManager.
    Deal with imap connection and process each mail in the inbox.
    """

    def __init__(
        self,
        logger: Logger,
        config: ImapConf,
        stop_event: Event,
        heartbeat: Heartbeat,
    ) -> None:
        self.logger = logger
        self._hostname = config.get(HOSTNAME_NAME)
        self._username = config.get(USERNAME_NAME)
        self._default_destination_folder = config.get(IMAP_DEFAULT_FOLDER_NAME)
        self._handler: IMAP4_SSL = None
        self.config = config
        self.running = False
        self._stop_event = stop_event
        self._heartbeat = heartbeat
        self.notifiers = Notifiers(logger, config)

        self._connect_with_retry()

        logger.info(
            "imapmanager initialized on %s with %s", self._hostname, self._username
        )

    def _connect(self) -> None:
        """
        Perform a single connection attempt and select the mailbox.
        Raise on any failure.
        """
        handler = IMAP4_SSL(
            self._hostname,
            self.config.get(PORT_NAME),
            ssl_context=create_default_context(),
            timeout=SOCKET_TIMEOUT,
        )
        handler.login(self._username, self.config.get(PASSWORD_NAME))
        handler.select(f'"{self.config.get(MAILBOX_NAME)}"')
        self._handler = handler  # affect the successful handler
        self.running = True
        self.logger.info("Successful connection as username=%s", self._username)

    def _connect_with_retry(self) -> bool:
        """
        Try to connect, retrying transient failures with exponential backoff.
        Network/SSL errors are retried forever (wait out the outage)
        Other errors (like login/auth errors) are retried before treated as fatal.
        :return     True if the connection is successful, False otherwise.
        """
        attempt = 0
        auth_failures = 0
        delay = RECONNECT_INITIAL_DELAY
        while not self._stop_event.is_set():
            try:
                self._connect()
            except TRANSIENT_ERRORS as exc:
                reason = exc
            except IMAP4.error as exc:  # -> Logical errors (login/auth etc...)
                auth_failures += 1
                if auth_failures >= RECONNECT_MAX_AUTH_ATTEMPTS:
                    self.panic(f"Login keeps failing: err={exc}")
                    return False
                reason = exc
            else:
                return True

            self._handler = None
            attempt += 1
            self.logger.warning(
                "Connection attempt %d failed, retrying in %ds: err=%s",
                attempt,
                delay,
                reason,
            )

            # Waiting out an outage is expected behaviour, not a stuck daemon.
            self._heartbeat.refresh(delay + HEARTBEAT_GRACE)

            if self._stop_event.wait(timeout=delay):
                return False
            delay = min(delay * RECONNECT_MULTIPLIER, RECONNECT_MAX_DELAY)
        return False

    def _maybe_reconnect(self) -> bool:
        """
        If handler is not connected yet or disconnected, reconnect it.
        :return     True if the connection is successful, False otherwise.
        """
        if self._handler is None:
            return self._connect_with_retry()
        try:
            if self._handler.check():
                return True
        except Exception as exc:  # noqa: BLE001 (blind-except)
            self.logger.warning(
                "Check connection failed, trying to reconnect: err=%s",
                exc,
            )
            self._handler = None
            return self._connect_with_retry()
        return False

    def _check_folder_exist_on_server(self, folder_name: str) -> bool:
        r"""
        Check that the given folder exists on the server.
        Folder on the server looks like (with a backslash removed):
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

    def process_mails(self, stop_event: Event) -> None:
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
            self._handler.select(f'"{mailbox}"')
        except Exception as exc:  # noqa: BLE001 (blind-except)
            self.logger.error("Failed to select, will retry: err=%s", exc)
            self._handler = None
            return

        try:
            # Get the unseen mails of this directory
            typ, data = self._handler.uid("SEARCH", None, "UNSEEN")
            if typ != "OK":
                self.panic(f"Fail to search for mails (data={data}), exiting...")
                return
        except Exception as exc:  # noqa: BLE001 (blind-except)
            self.logger.error("Failed to search, will retry: err=%s", exc)
            self._handler = None
            return

        for uid_bytes in data[0].split():
            if stop_event.is_set():
                return
            # Keep a slow backlog healthy: each mail processed is progress.
            self._heartbeat.refresh()
            uid = uid_bytes.decode()

            mail_subject = ""
            mail_action = MailAction()

            # Fetch and process mail
            try:
                # See the mail without changing its unread flag
                typ, data = self._handler.uid("FETCH", uid, "(BODY.PEEK[])")
                if typ != "OK":
                    self.panic(
                        f'Fail to fetch mail with uid="{uid}" (data={data}), exiting...'
                    )
                    return
                # If the mail no longer exists, UID FETCH returns OK with empty data.
                # Skip it.
                if not data or data[0] is None:
                    self.logger.warning(
                        'Mail with uid="%s" no longer exists, skipping', uid
                    )
                    continue
                # data[0][1] is the raw email
                mail_msg: EmailMessage = email.message_from_bytes(
                    data[0][1], policy=policy.default
                )

                mail_subject = decode_subject(mail_msg[IMAP_SUBJECT])
                mail_body: EmailMessage = mail_msg.get_body(
                    preferencelist=("plain", "html")
                )
                if mail_body:
                    try:
                        mail_body = mail_body.get_content()
                    except LookupError:
                        # Encoding error, fallback to raw payload decoding.
                        raw = mail_body.get_payload(decode=True)
                        if raw is not None:
                            charset = mail_body.get_content_charset("utf-8")
                            try:
                                mail_body = raw.decode(charset, errors="replace")
                            except LookupError:
                                try:
                                    mail_body = raw.decode("utf-8", errors="replace")
                                except LookupError:
                                    # Give up with the mail
                                    self.logger.warning("Impossible to decode the body")
                                    mail_body = None
                        else:
                            mail_body = None

                mail_action = self._unsafe_get_mail_action(
                    mail_msg, mail_subject, mail_body
                )
            except TRANSIENT_ERRORS as exc:
                self.logger.warning(
                    "Connection lost while fetching a mail, will reconnect: err=%s", exc
                )
                self._handler = None
                return
            except Exception:
                mail_action.folder = self._default_destination_folder
                self.logger.exception(
                    'Error processing an email, moving it into folder="%s"',
                    mail_action.folder,
                )

            self.logger.info(
                'GET mail subject="%s" from="%s" dest="%s" to be moved into "%s" '
                "(notifiers=%s, mark_as_read=%s, rule=%s)",
                mail_subject,
                mail_action.mail_from,
                mail_action.mail_dest,
                mail_action.folder,
                mail_action.notifiers,
                mail_action.mark_as_read,
                mail_action.rule_name,
            )

            # Send the notifications if needed
            if mail_action.notifiers:
                self.notifiers.send(
                    f'GET mail subject="{mail_subject}" from="{mail_action.mail_from}"',
                    mail_action.notifiers,
                )

            try:
                # Check if the folder exists on the server
                if not self._check_folder_exist_on_server(mail_action.folder):
                    self.logger.warning(
                        'folder="%s" does not exist on the server, moving the mail '
                        'into the default folder="%s"',
                        mail_action.folder,
                        self._default_destination_folder,
                    )
                    mail_action.folder = self._default_destination_folder
                    # We don't want to silently mark as read mails that ends in the
                    # wrong folder.
                    mail_action.mark_as_read = False
                    if not self._check_folder_exist_on_server(mail_action.folder):
                        self.panic(
                            f'default folder="{mail_action.folder}" does not exist '
                            "on the server, please fix the configuration, exiting..."
                        )
                        return

                # Mark the mail as read if needed
                if mail_action.mark_as_read:
                    typ, data = self._handler.uid("STORE", uid, "+FLAGS", "\\Seen")
                    if typ != "OK":
                        self.panic(
                            f'Fail to mark mail with subject="{mail_subject}" as read '
                            f"(data={data}), exiting..."
                        )
                        return

                # Copy the mail into the folder
                typ, data = self._handler.uid("COPY", uid, f'"{mail_action.folder}"')
                if typ != "OK":
                    self.panic(
                        f'Mail with subject="{mail_subject}" not copied to '
                        f'folder="{mail_action.folder}" (data={data}), exiting...'
                    )
                    return

                # Delete the original mail
                typ, data = self._handler.uid("STORE", uid, "+FLAGS", "\\Deleted")
                if typ != "OK":
                    self.panic(
                        f'Fail to delete original mail with subject="{mail_subject}" '
                        f"(data={data}), exiting..."
                    )
                    return

                typ, data = self._handler.uid("EXPUNGE", uid)
                if typ != "OK":
                    self.panic(
                        f'Fail to expunge original mail with subject="{mail_subject}" '
                        f"(data={data}), exiting..."
                    )
                    return
            except TRANSIENT_ERRORS as exc:
                self.logger.warning(
                    "Connection lost while applying actions to a mail, will reconnect: "
                    "err=%s",
                    exc,
                )
                self._handler = None
                return

    def _analyse_filters_for_category(
        self,
        category: str,
        category_name: str,
        input_values: list[str],
    ) -> MailAction:
        """
        Check if at least one param of input_values is matching the given category
        by checking all its rules and filters.
        All matching rules are collected and the one with the highest weight
        is returned (same weight means first arrived).
        :param      category    the config section to check (SUBJECT, FROM, DEST, ...)
        :param      category_name   the name of the category (subject, from, to, cc, ..)
        :param      input_values    the values to check against the rule patterns
        :return     result  result of type MailAction.
        """
        self.logger.debug("starting analysis of category %s", category_name)
        all_matches = MailActions(self.logger)

        # Get all rules for the category
        rules = self.config[SECTION_FILTERS_NAME].get(category)
        if not rules:
            return MailAction()

        # A rule has a list of rule composed of rules and filters
        for target_folder, filter_entries in rules.items():
            # Check every filter in the order
            for filter_entry in filter_entries:
                # For this filter, check if at least one input_values matches
                # one of its patterns. filter_entry looks like:
                #   {pattern: '[SPAM]', actions: [move, mark_as_read]}
                #   {pattern: ['[SPAM]', '*** SPAM ***'], actions: [move]}
                # An optional 'weight' can be found.
                # A filter with several patterns stays a single rule: it matches as
                # soon as one of its patterns matches.
                matched_pattern = next(
                    (
                        pattern
                        for pattern in normalize_patterns(
                            filter_entry[FILTER_PATTERN_NAME]
                        )
                        for input_value in input_values
                        if pattern.lower() in input_value.lower()
                    ),
                    None,
                )
                if matched_pattern is not None:
                    matched_actions = filter_entry[FILTER_ACTIONS_NAME]
                    mail_action = MailAction(
                        rule_name=category_name,
                        weight=filter_entry.get(
                            FILTER_WEIGHT_NAME,
                            self.config.get(WEIGHT_NAME, DEFAULT_WEIGHT),
                        ),
                        folder=target_folder
                        if FILTER_ACTION_MOVE_NAME in matched_actions
                        else None,
                        notifiers=tuple(
                            notifier
                            for notifier in NOTIFIERS
                            if notifier in matched_actions
                        ),
                        mark_as_read=FILTER_ACTION_MARK_AS_READ_NAME in matched_actions,
                    )

                    self.logger.debug(
                        "Got a match for category=%s filter_pattern=%s folder=%s "
                        "weight=%d",
                        category_name,
                        matched_pattern,
                        mail_action.folder,
                        mail_action.weight,
                    )
                    all_matches.append(mail_action)

        return all_matches.get_best_action()

    def _unsafe_get_mail_action(
        self, raw_email: str, mail_subject: str, mail_body: str
    ) -> MailAction:
        """
        Determine the best MailAction for a given mail by evaluating all filter
        categories (subject, body, from, to, cc).
        """
        all_actions = MailActions(self.logger)
        mail_dest = []

        # Check if the mail has a 'subject' rule
        if mail_subject:
            all_actions.append(
                self._analyse_filters_for_category(
                    SECTION_SUBJECT_NAME,
                    IMAP_SUBJECT,
                    [mail_subject],
                )
            )

        # Check if the mail has a 'body' rule
        if mail_body:
            all_actions.append(
                self._analyse_filters_for_category(
                    SECTION_BODY_NAME, IMAP_BODY, [mail_body]
                )
            )

        # Check if the mail has a 'from' rule
        mail_from: str | None = None
        raw_from = raw_email[IMAP_FROM]
        self.logger.debug('raw field from="%s"', raw_from)
        mail_from = extract_and_sanitize_mail_addresses(raw_from)
        # The list can be empty after <extract_and_sanitize_mail_addresses>
        if mail_from:
            # We don't want to deal with multiple senders
            mail_from = mail_from[0]
            all_actions.append(
                self._analyse_filters_for_category(
                    SECTION_FROM_NAME, IMAP_FROM, [mail_from]
                )
            )

        # Check if the mail has a 'to' rule
        mail_to = raw_email[IMAP_TO]
        self.logger.debug('raw field to="%s"', mail_to)
        mail_to = extract_and_sanitize_mail_addresses(mail_to)
        # The list can be empty after <extract_and_sanitize_mail_addresses>
        if mail_to:
            mail_dest.extend(mail_to)
            all_actions.append(
                self._analyse_filters_for_category(SECTION_DEST_NAME, IMAP_TO, mail_to)
            )

        # Check if the mail has a 'cc' rule
        # The values checked for the 'cc' rules are the ones of the 'to' rules
        mail_cc = raw_email[IMAP_CC]
        self.logger.debug('raw field cc="%s"', mail_cc)
        mail_cc = extract_and_sanitize_mail_addresses(mail_cc)
        # The list can be empty after <extract_and_sanitize_mail_addresses>
        if mail_cc:
            mail_dest.extend(mail_cc)
            all_actions.append(
                self._analyse_filters_for_category(SECTION_DEST_NAME, IMAP_CC, mail_cc)
            )

        mail_action = all_actions.get_best_action()
        mail_action.mail_from = mail_from
        mail_action.mail_dest = mail_dest

        # If we still don't have a rule for the mail, take the default folder
        if not mail_action.folder:
            self.logger.debug("No rule for the mail, moving it into the default folder")
            mail_action.folder = self._default_destination_folder

        return mail_action

    def panic(self, msg: str) -> None:
        """
        Log a critical message and send it through every configured notifier.
        """
        self.running = False

        self.logger.critical(msg)

        # Notify through every notifier defined in the configuration
        self.notifiers.send(msg)

        self.logout()

        # As panic is fatal: stop the daemon.
        self._stop_event.set()

    def logout(self) -> None:
        """
        Logout and close the mail handler.
        """
        if not self._handler:
            return

        # CLOSE is only valid in the SELECTED state.
        if getattr(self._handler, "state", None) == "SELECTED":
            try:
                self._handler.close()
            except Exception as exc:  # noqa: BLE001 (blind-except)
                self.logger.error("Failed to close mailbox: err=%s", exc)

        try:
            self._handler.logout()
            self.logger.info("Successful disconnection")
        except Exception as exc:  # noqa: BLE001 (blind-except)
            self.logger.error("Failed to logout: err=%s", exc)
        finally:
            self._handler = None
