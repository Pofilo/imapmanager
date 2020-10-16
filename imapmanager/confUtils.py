'''
confUtils.py: useful and general methods for the configuration.

imap-manager: Connect and manage your mail account through IMAP.
Copyright (C) 2018-2020 pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.

'''


import configparser
import sys
import logging

import utils

logger = logging.getLogger('imapmanager')

def check_config(config):
    # Check all section exist
    check_config_section(config, utils.SECTION_GENERAL_NAME)
    check_config_section(config, utils.SECTION_SUBJECT_NAME)
    check_config_section(config, utils.SECTION_FROM_NAME)
    check_config_section(config, utils.SECTION_TO_NAME)

    # Check all mandatories keys
    check_config_key(config, utils.SECTION_GENERAL_NAME, utils.HOSTNAME_NAME)
    check_config_key(config, utils.SECTION_GENERAL_NAME, utils.PORT_NAME)
    check_config_key(config, utils.SECTION_GENERAL_NAME, utils.USERNAME_NAME)
    check_config_key(config, utils.SECTION_GENERAL_NAME, utils.PASSWORD_NAME)
    check_config_key(config, utils.SECTION_GENERAL_NAME, utils.MAILBOX_NAME)
    check_config_key(config, utils.SECTION_GENERAL_NAME, utils.POLLING_INTERVAL_NAME)
    check_config_key(config, utils.SECTION_GENERAL_NAME, utils.IMAP_DEFAULT_FOLDER_NAME)

def check_config_section(config, section):
    if not config.has_section(section):
        logger.critical('No section "{}" in config file'.format(section))
        sys.exit(1)

def check_config_key(config, section, key):
    if not config.has_option(section, key):
        logger.critical('No key "{}" in section "{}" in config file'.format(key, section))
        sys.exit(1)

