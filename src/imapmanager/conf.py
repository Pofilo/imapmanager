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

import configparser
from logging import Logger
from os import getenv, path
from sys import exit

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
    SECTION_DEST_NAME,
    SECTION_FROM_NAME,
    SECTION_GENERAL_NAME,
    SECTION_SUBJECT_NAME,
    USERNAME_NAME,
)


class ImapConf:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger
        self._config_path = None
        self._config = None

        # Open and load config file
        self._open_and_load_config()
        # Check if config is valid
        self._check_config()

    def _open_and_load_config(self):
        """
        Method to open and load the configuration file.
        """
        # TODO: use argparse instead of env
        self._config_path = getenv(CONFIG_PATH_NAME, DEFAULT_CONFIG_PATH)

        if path.isfile(self._config_path):
            self._config = configparser.ConfigParser()
            try:
                self._config.read(self._config_path)
            except configparser.ParsingError as exc:
                self.logger.exception("Parsing while reading conf: exc=%s", exc)
                exit(1)
        else:
            self.logger.critical(
                "config_file=%s not found, or set the env variable %s accordingly",
                self._config_path,
                CONFIG_PATH_NAME,
            )
            exit(1)

    def _check_config(self):
        """
        Method used to check if the configuration is valid
        (aka contains all mandatory fields).
        """

        # TODO: better use a map/array of the mandatory section/keys rather than
        # calling each one individually

        # Check all section exist
        self._check_config_section(SECTION_GENERAL_NAME)
        self._check_config_section(SECTION_SUBJECT_NAME)
        self._check_config_section(SECTION_FROM_NAME)
        self._check_config_section(SECTION_DEST_NAME)

        # Check all mandatories keys
        self._check_config_key(SECTION_GENERAL_NAME, HOSTNAME_NAME)
        self._check_config_key(SECTION_GENERAL_NAME, PORT_NAME)
        self._check_config_key(SECTION_GENERAL_NAME, USERNAME_NAME)
        self._check_config_key(SECTION_GENERAL_NAME, PASSWORD_NAME)
        self._check_config_key(SECTION_GENERAL_NAME, MAILBOX_NAME)
        self._check_config_key(SECTION_GENERAL_NAME, POLLING_INTERVAL_NAME)
        self._check_config_key(SECTION_GENERAL_NAME, IMAP_DEFAULT_FOLDER_NAME)
        self._check_config_key(SECTION_GENERAL_NAME, LOG_LEVEL_NAME)

    def _check_config_section(self, section):
        """
        Check that the given section exists in the configuration.
        :param      section     the section to check
        Log and exit if the section is not found.
        """
        if not self._config.has_section(section):
            self.logger.critical("section=%s not found in config file", section)
            exit(1)

    def _check_config_key(self, section, key):
        """
        Check that the given key exists in the given section of the configuration.
        :param      section     the section to check
        :param      key         the key to check
        Log and exit if the key (or the section) is not found.
        """
        if not self._config.has_option(section, key):
            self.logger.critical(
                "key=%s not found in section=%s in config file", key, section
            )
            exit(1)

    def get(self, section, key):
        return self._config.get(section, key)
