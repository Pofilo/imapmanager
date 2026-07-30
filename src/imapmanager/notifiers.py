"""
notifiers.py: send notifications through the configured notifiers.

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

from typing import TYPE_CHECKING

import requests

from imapmanager.constants import (
    FILTER_ACTION_PUSHOVER_NAME,
    FILTER_ACTION_TELEGRAM_NAME,
    NOTIFIERS,
    PUSHOVER_TOKEN_NAME,
    PUSHOVER_USER_KEY_NAME,
    SECTION_PUSHOVER_NAME,
    SECTION_TELEGRAM_NAME,
    TELEGRAM_CHAT_ID_NAME,
    TELEGRAM_TOKEN_NAME,
)
from imapmanager.utils import redact

if TYPE_CHECKING:
    from logging import Logger

    from imapmanager.conf import ImapConf

HTTP_CODE_SUCCESS = 200
NOTIFICATION_TIMEOUT = 5  # seconds


class Notifiers:
    """
    Send notifications through the notifiers defined in the configuration.
    A notifier without its section in the configuration is simply skipped.
    """

    def __init__(self, logger: Logger, config: ImapConf) -> None:
        self.logger = logger
        self.config = config
        # One request builder per notifier of <NOTIFIERS>
        self._builders = {
            FILTER_ACTION_TELEGRAM_NAME: self._telegram_request,
            FILTER_ACTION_PUSHOVER_NAME: self._pushover_request,
        }

    def _telegram_request(self, message: str) -> tuple[str, dict[str, str]]:
        """
        Build the telegram request (url and form fields) sending <message>.
        """
        section = self.config[SECTION_TELEGRAM_NAME]
        return (
            f"https://api.telegram.org/bot{section[TELEGRAM_TOKEN_NAME]}/sendMessage",
            {"chat_id": section[TELEGRAM_CHAT_ID_NAME], "text": message},
        )

    def _pushover_request(self, message: str) -> tuple[str, dict[str, str]]:
        """
        Build the pushover request (url and form fields) sending <message>.
        """
        section = self.config[SECTION_PUSHOVER_NAME]
        return (
            "https://api.pushover.net/1/messages.json",
            {
                "token": section[PUSHOVER_TOKEN_NAME],
                "user": section[PUSHOVER_USER_KEY_NAME],
                "message": message,
            },
        )

    def _send_one(self, name: str, message: str) -> None:
        """
        Send <message> through the <name> notifier if it is configured
        (aka if its section is defined in the configuration).
        :param      name        the notifier name (a key of <NOTIFIERS>)
        :param      message     the message to send
        Never raises: a failing notification must not break the mail loop.
        """
        section, _ = NOTIFIERS[name]
        if not self.config.get(section):
            return

        try:
            url, fields = self._builders[name](message)
            resp = requests.post(url, data=fields, timeout=NOTIFICATION_TIMEOUT)
            if resp.status_code != HTTP_CODE_SUCCESS:
                self.logger.warning(
                    "Failed to send %s message, status_code=%s err=%s",
                    name,
                    resp.status_code,
                    # A proxy answering an error often echoes the requested URL.
                    redact(resp.text, self.config),
                )
        except Exception as exc:  # noqa: BLE001 (blind-except)
            # Never log the traceback: it ends with the <requests> message, which
            # carries the request URL and so the telegram token it holds.
            self.logger.error(
                "Failed to send %s message: err=%s",
                name,
                redact(f"{type(exc).__name__}: {exc}", self.config),
            )

    def send(self, message: str, names: tuple[str, ...] | None = None) -> None:
        """
        Send <message> through the given notifiers.
        :param      message     the message to send
        :param      names       the notifiers to use
        Every known notifier is used when <names> is None.
        """
        for name in NOTIFIERS if names is None else names:
            self._send_one(name, message)
