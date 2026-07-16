"""
conf.py: conf class for imapmanager.

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

from collections import UserDict
from copy import deepcopy
from json import dumps
from os import getenv
from pathlib import Path
from sys import exit as sys_exit
from typing import TYPE_CHECKING

from yaml import SafeLoader, load

from imapmanager.constants import (
    CONFIG_PATH_NAME,
    DEFAULT_CONFIG_PATH,
    FILTER_ACTION_MARK_AS_READ_NAME,
    FILTER_ACTION_MOVE_NAME,
    FILTER_ACTION_TELEGRAM_NAME,
    FILTER_ACTIONS_NAME,
    FILTER_PATTERN_NAME,
    HOSTNAME_NAME,
    IMAP_DEFAULT_FOLDER_NAME,
    LOG_LEVEL_NAME,
    MAILBOX_NAME,
    PASSWORD_NAME,
    POLLING_INTERVAL_NAME,
    PORT_NAME,
    SECTION_BODY_NAME,
    SECTION_DEST_NAME,
    SECTION_FILTERS_NAME,
    SECTION_FROM_NAME,
    SECTION_SUBJECT_NAME,
    SECTION_TELEGRAM_NAME,
    TELEGRAM_CHAT_ID_NAME,
    TELEGRAM_TOKEN_NAME,
    USERNAME_NAME,
)

if TYPE_CHECKING:
    from logging import Logger


class ImapConf(UserDict):
    """
    Class loading the conf file as yaml and exposing the conf as a dict.
    """

    def __init__(self, logger: Logger, *args: tuple, **kwargs: dict) -> None:
        super().__init__(*args, **kwargs)
        self.logger = logger
        self._config_path = None

        # Open and load config file
        self._open_and_load_config()

    def _open_and_load_config(self) -> None:
        """
        Open and load the configuration file.
        """
        # TODO(pofilo): use argparse instead of env
        # 029
        self._config_path = getenv(CONFIG_PATH_NAME, DEFAULT_CONFIG_PATH)

        if Path(self._config_path).is_file():
            try:
                with Path(self._config_path).open("r", encoding="UTF-8") as file_fd:
                    self.data = load(file_fd, Loader=SafeLoader)
                    # Check if config is valid
                    self._check_config()
                    if self.data.get(LOG_LEVEL_NAME) == "DEBUG":
                        conf = deepcopy(self.data)
                        conf[PASSWORD_NAME] = "*****"
                        if conf.get(SECTION_TELEGRAM_NAME):
                            conf[SECTION_TELEGRAM_NAME][TELEGRAM_TOKEN_NAME] = "*****"
                            conf[SECTION_TELEGRAM_NAME][TELEGRAM_CHAT_ID_NAME] = "*****"
                        self.logger.debug("conf used:\n%s", dumps(conf, indent=2))
            except Exception as exc:  # noqa: BLE001 (blind-except)
                self.logger.error("Parsing while reading conf: %s", exc)
                sys_exit(1)
        else:
            self.logger.critical(
                "config_file=%s not found, or set the env variable %s accordingly",
                self._config_path,
                CONFIG_PATH_NAME,
            )
            sys_exit(1)

    def _check_config(self) -> None:
        """
        Check if the configuration is valid
        (aka contains all mandatory fields).
        """
        # Check all mandatories keys
        self._check_config_key(SECTION_FILTERS_NAME)
        self._check_filters()
        self._check_telegram()

        self._check_config_key(HOSTNAME_NAME)
        self._check_config_key(PORT_NAME)
        self._check_config_key(USERNAME_NAME)
        self._check_config_key(PASSWORD_NAME)
        self._check_config_key(MAILBOX_NAME)
        self._check_config_key(POLLING_INTERVAL_NAME)
        self._check_config_key(IMAP_DEFAULT_FOLDER_NAME)
        self._check_config_key(LOG_LEVEL_NAME)

    def _check_config_key(self, key: str) -> None:
        """
        Check that the given key exists in the configuration.
        :param      key         the key to check
        Log and exit if the key (or the section) is not found.
        """
        if not self.data.get(key):
            self.logger.critical("key=%s not found in config file", key)
            sys_exit(1)

    def _check_telegram(self) -> None:
        """
        Check that the optional telegram section, when present,
        contains the mandatory <token> and <chat_id> keys.
        Log and exit if a key is missing.
        """
        telegram = self.data.get(SECTION_TELEGRAM_NAME)
        if not telegram:
            return
        for key in (TELEGRAM_TOKEN_NAME, TELEGRAM_CHAT_ID_NAME):
            if not isinstance(telegram, dict) or not telegram.get(key):
                self.logger.critical(
                    "key=%s not found in section=%s of config file",
                    key,
                    SECTION_TELEGRAM_NAME,
                )
                sys_exit(1)

    def _check_filters(self) -> None:
        """
        Check that every filter entry in every category has the mandatory
        <pattern> and <actions> keys.
        Log and exit on the first invalid entry found.
        """
        filters = self.data.get(SECTION_FILTERS_NAME, {})
        categories = [
            SECTION_SUBJECT_NAME,
            SECTION_BODY_NAME,
            SECTION_FROM_NAME,
            SECTION_DEST_NAME,
        ]
        for category in filters:
            if category not in categories:
                self.logger.critical("category=%s unknown", category)
                sys_exit(1)
            for folder, entries in filters[category].items():
                for index, entry in enumerate(entries):
                    # Maybe we could also check if there is unknown fields
                    for mandatory_field in (FILTER_PATTERN_NAME, FILTER_ACTIONS_NAME):
                        if mandatory_field not in entry:
                            self.logger.critical(
                                "key=%s not found in filter=filters.%s.%s[%d]",
                                mandatory_field,
                                category,
                                folder,
                                index,
                            )
                            sys_exit(1)
                    for action in entry[FILTER_ACTIONS_NAME]:
                        if action not in (
                            FILTER_ACTION_MARK_AS_READ_NAME,
                            FILTER_ACTION_MOVE_NAME,
                            FILTER_ACTION_TELEGRAM_NAME,
                        ):
                            self.logger.critical(
                                "unknown action=%s in filter=filters.%s.%s[%d]",
                                action,
                                category,
                                folder,
                                index,
                            )
                            sys_exit(1)
