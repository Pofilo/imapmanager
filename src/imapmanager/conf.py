"""
conf.py: conf class for imapmanager.

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

from collections import UserDict
from copy import deepcopy
from json import dumps
from logging import Logger
from os import getenv, path
from sys import exit as sys_exit
from yaml import load, SafeLoader

from imapmanager.constants import (
    CONFIG_PATH_NAME,
    DEFAULT_CONFIG_PATH,
    IMAP_DEFAULT_FOLDER_NAME,
    LOG_LEVEL_NAME,
    HOSTNAME_NAME,
    MAILBOX_NAME,
    PASSWORD_NAME,
    POLLING_INTERVAL_NAME,
    PORT_NAME,
    SECTION_FILTERS_NAME,
    SECTION_TELEGRAM_NAME,
    TELEGRAM_CHAT_ID_NAME,
    TELEGRAM_TOKEN_NAME,
    USERNAME_NAME,
)


class ImapConf(UserDict):
    """
    Class loading the conf file as yaml and exposing the conf as a dict.
    """

    def __init__(self, logger: Logger, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.logger = logger
        self._config_path = None

        # Open and load config file
        self._open_and_load_config()

    def _open_and_load_config(self):
        """
        Method to open and load the configuration file.
        """
        # TODO: use argparse instead of env
        self._config_path = getenv(CONFIG_PATH_NAME, DEFAULT_CONFIG_PATH)

        if path.isfile(self._config_path):
            try:
                with open(self._config_path, "r", encoding="UTF-8") as file_fd:
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
            except Exception as exc:
                self.logger.error("Parsing while reading conf: exc=%s", exc)
                sys_exit(1)
        else:
            self.logger.critical(
                "config_file=%s not found, or set the env variable %s accordingly",
                self._config_path,
                CONFIG_PATH_NAME,
            )
            sys_exit(1)

    def _check_config(self):
        """
        Method used to check if the configuration is valid
        (aka contains all mandatory fields).
        """

        # Check all mandatories keys
        self._check_config_key(SECTION_FILTERS_NAME)

        self._check_config_key(HOSTNAME_NAME)
        self._check_config_key(PORT_NAME)
        self._check_config_key(USERNAME_NAME)
        self._check_config_key(PASSWORD_NAME)
        self._check_config_key(MAILBOX_NAME)
        self._check_config_key(POLLING_INTERVAL_NAME)
        self._check_config_key(IMAP_DEFAULT_FOLDER_NAME)
        self._check_config_key(LOG_LEVEL_NAME)

    def _check_config_key(self, key):
        """
        Check that the given key exists in the configuration.
        :param      key         the key to check
        Log and exit if the key (or the section) is not found.
        """
        if not self.data.get(key):
            self.logger.critical("key=%s not found in config file", key)
            sys_exit(1)
