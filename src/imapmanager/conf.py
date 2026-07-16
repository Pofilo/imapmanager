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
from logging import getLevelNamesMapping
from os import getenv
from pathlib import Path
from sys import exit as sys_exit
from typing import TYPE_CHECKING

from yaml import SafeLoader, YAMLError, load

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
                    data = load(file_fd, Loader=SafeLoader)
            except YAMLError as exc:
                self.logger.critical("Parsing while reading conf: %s", exc)
                sys_exit(1)
            except OSError as exc:
                self.logger.critical("Reading conf: %s", exc)
                sys_exit(1)
            if not isinstance(data, dict):
                self.logger.critical(
                    "config_file=%s must contain a YAML mapping, got %s",
                    self._config_path,
                    type(data).__name__,
                )
                sys_exit(1)
            self.data = data
            # Check if config is valid
            self._check_config()
            if self.data.get(LOG_LEVEL_NAME) == "DEBUG":
                conf = deepcopy(self.data)
                conf[PASSWORD_NAME] = "*****"
                if conf.get(SECTION_TELEGRAM_NAME):
                    conf[SECTION_TELEGRAM_NAME][TELEGRAM_TOKEN_NAME] = "*****"
                    conf[SECTION_TELEGRAM_NAME][TELEGRAM_CHAT_ID_NAME] = "*****"
                self.logger.debug("conf used:\n%s", dumps(conf, indent=2, default=str))
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
        self._check_config_key(SECTION_FILTERS_NAME, dict)
        self._check_filters()
        self._check_telegram()

        self._check_config_key(HOSTNAME_NAME)
        self._check_config_key(PORT_NAME, int, minimum=1, maximum=65535)
        self._check_config_key(USERNAME_NAME)
        self._check_config_key(PASSWORD_NAME)
        self._check_config_key(MAILBOX_NAME)
        self._check_config_key(POLLING_INTERVAL_NAME, (int, float), minimum=1)
        self._check_config_key(IMAP_DEFAULT_FOLDER_NAME)
        self._check_config_key(LOG_LEVEL_NAME)
        self._check_log_level()

    def _check_config_key(
        self,
        key: str,
        expected_type: type | tuple[type, ...] = str,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> None:
        """
        Check that the given key exists in the configuration with a non-empty
        value of the expected type, within the given range if any.
        :param      key             the key to check
        :param      expected_type   the type(s) the value must have
        :param      minimum         the minimum value allowed (numbers only)
        :param      maximum         the maximum value allowed (numbers only)
        Log and exit if the key is missing or its value is invalid.
        """
        value = self.data.get(key)
        if value is None:
            self.logger.critical("key=%s not found in config file", key)
            sys_exit(1)
        types = expected_type if isinstance(expected_type, tuple) else (expected_type,)
        # bool is a subclass of int but is never a valid config value
        if isinstance(value, bool) or not isinstance(value, types):
            self.logger.critical(
                "key=%s must be of type %s, got %s",
                key,
                " or ".join(one_type.__name__ for one_type in types),
                type(value).__name__,
            )
            sys_exit(1)
        if isinstance(value, (str, dict)) and not value:
            self.logger.critical("key=%s is empty in config file", key)
            sys_exit(1)
        if minimum is not None and value < minimum:
            self.logger.critical("key=%s must be >= %s, got %s", key, minimum, value)
            sys_exit(1)
        if maximum is not None and value > maximum:
            self.logger.critical("key=%s must be <= %s, got %s", key, maximum, value)
            sys_exit(1)

    def _check_log_level(self) -> None:
        """
        Check that the logLevel value is a known logging level name.
        Log and exit otherwise.
        """
        log_level = self.data.get(LOG_LEVEL_NAME)
        level_names = getLevelNamesMapping()
        if log_level not in level_names:
            self.logger.critical(
                "logLevel=%s unknown, expected one of: %s",
                log_level,
                ", ".join(level_names),
            )
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
            if not isinstance(filters[category], dict):
                self.logger.critical(
                    "filters.%s must be a mapping of folders", category
                )
                sys_exit(1)
            for folder, entries in filters[category].items():
                if not isinstance(entries, list):
                    self.logger.critical(
                        "filters.%s.%s must be a list of filters", category, folder
                    )
                    sys_exit(1)
                for index, entry in enumerate(entries):
                    self._check_filter_entry(category, folder, index, entry)

    def _check_filter_entry(
        self, category: str, folder: str, index: int, entry: dict
    ) -> None:
        """
        Check that the given filter entry is a mapping with the mandatory
        <pattern> and <actions> keys, and that every action is known.
        Log and exit on the first invalid field found.
        """
        if not isinstance(entry, dict):
            self.logger.critical(
                "filter=filters.%s.%s[%d] must be a mapping",
                category,
                folder,
                index,
            )
            sys_exit(1)
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
