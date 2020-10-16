'''
utils.py: useful and general methods for imap-manager.

imap-manager: Connect and manage your mail account through IMAP.
Copyright (C) 2016-2020 pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.

'''

import configparser, argparse
import re, quopri, base64, sys, os.path
import logging

logger = logging.getLogger('imapmanager')

### CONFIGURATION VARIABLES NAMES ###
SECTION_GENERAL_NAME = 'GENERAL'
HOSTNAME_NAME = 'IMAP_HOSTNAME'
PORT_NAME = 'IMAP_PORT'
USERNAME_NAME = 'IMAP_USERNAME'
PASSWORD_NAME = 'IMAP_PASSWORD'
MAILBOX_NAME = 'IMAP_MAILBOX'
POLLING_INTERVAL_NAME = 'POLLING_INTERVAL'
IMAP_DEFAULT_FOLDER_NAME = 'DEFAULT_FOLDER'
LOG_LEVEL = 'LOG_LEVEL'
SECTION_SUBJECT_NAME = 'SUBJECT'
SECTION_FROM_NAME = 'FROM'
SECTION_TO_NAME = 'TO'

### IMAP VARIABLES ###
IMAP_SUBJECT = 'subject'
IMAP_FROM = 'from'
IMAP_TO = 'to'

### DEFAULT VARIABLES ###
DEFAULT_CONFIG_PATH = '../config/imapmanager.conf'
ENCODING = 'utf8'

### FUNCTIONS ###

def clean_mail_address(address):
    """
    Clean the given mail address.
    "Name LASTNAME" <name.lastname@example.com>
    will become: name.lastname@example.com
    :param      address     the mail address to clean
    """
    # Remove <> added by some client and only get the content inside
    if '<' in address:
        address = address.split('<')[1]
        if '>' in address:
            address = address.split('>')[0]

    return address

# Credits: https://stackoverflow.com/a/43393449
def decode_subject(subject):
    pattern = re.compile(r'(([^=]*)=\?([^\?]*)\?([BbQq])\?([^\?]*)\?=([^=]*))', re.IGNORECASE)
    data = pattern.findall(subject)
    line = []
    if data:
        for g in data:
            (raw,extra1,encoding,method,string,extra) = g
            extra1 = extra1.replace('\r','').replace('\n','').strip()
            if len(extra1) > 0:
                line.append(extra1)
            if method.lower() == 'q':
                string = quopri.decodestring(string)
                string = string.decode(encoding,errors='ignore')
                string = string.replace("_"," ").strip()
            if method.lower() == 'b':
                string = base64.b64decode(string)
                string = string.decode(encoding,errors='ignore')
            line.append(string)
            extra = extra.replace('\r','').replace('\n','').strip()
            if len(extra) > 0:
                line.append(extra)
        subject = "".join(line)

    return subject

def check_python_version():
    """
    Log and exit if the python version is not supported.
    """
    if sys.version_info <= (3, 7):
        logger.critical('The script needs at least python 3.7')
        sys.exit(1)

def open_and_load_config():
    """
    Function to parse arguments and then open and load the configuration file.
    :param  args        the arguments given to the program and parsed by argparse
    """

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--conf', '-c', dest='config_path')
    args = parser.parse_args()

    # Open and load config file
    if args.config_path:
        config_path = args.config_path
    else:
        config_path = DEFAULT_CONFIG_PATH
    config = configparser.ConfigParser()

    if os.path.isfile(config_path):
        try:
            config.read(config_path)
        except configparser.ParsingError as error:
            logger.critical('Parsing error: {}'.format(str(error)))
            sys.exit(1)
    else:
        logger.critical('Config file "{}" not found."'.format(config_path))
        sys.exit(1)

    # Check if config is valid
    check_config(config)

    return config, config_path

def check_config(config):
    """
    Function used to check if the configuration is valid (contains all mandatory fields).
    :param      config      the configuration to check
    """

    # TODO: better use a map/array of the mandatory section/keys rather than calling each one individually

    # Check all section exist
    __check_config_section(config, SECTION_GENERAL_NAME)
    __check_config_section(config, SECTION_SUBJECT_NAME)
    __check_config_section(config, SECTION_FROM_NAME)
    __check_config_section(config, SECTION_TO_NAME)

    # Check all mandatories keys
    __check_config_key(config, SECTION_GENERAL_NAME, HOSTNAME_NAME)
    __check_config_key(config, SECTION_GENERAL_NAME, PORT_NAME)
    __check_config_key(config, SECTION_GENERAL_NAME, USERNAME_NAME)
    __check_config_key(config, SECTION_GENERAL_NAME, PASSWORD_NAME)
    __check_config_key(config, SECTION_GENERAL_NAME, MAILBOX_NAME)
    __check_config_key(config, SECTION_GENERAL_NAME, POLLING_INTERVAL_NAME)
    __check_config_key(config, SECTION_GENERAL_NAME, IMAP_DEFAULT_FOLDER_NAME)

def __check_config_section(config, section):
    """
    Check that the given section exists in the configuration.
    :param      config      the configuration representation
    :param      section     the section to check
    Log and exit if the section is not found.
    """
    if not config.has_section(section):
        logger.critical('No section "{}" in config file'.format(section))
        sys.exit(1)

def __check_config_key(config, section, key):
    """
    Check that the given key exists in the given section of the configuration.
    :param      config      the configuration representation
    :param      section     the section to check
    :param      key         the key to check
    Log and exit if the key (or the section) is not found.
    """
    if not config.has_option(section, key):
        logger.critical('No key "{}" in section "{}" in config file'.format(key, section))
        sys.exit(1)

