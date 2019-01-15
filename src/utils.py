'''
utils.py: useful and general methods for imap-manager.

imap-manager: Connect and manage your mail account through IMAP.
Copyright (C) 2016-2018 pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.

'''


import re, quopri, base64, sys

from logger import Logger, FATAL, ERROR, WARN, INFO, DEBUG

my_logger = Logger()

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
IMAP_SUBJECT = 'subject'
SECTION_FROM_NAME = 'FROM'
IMAP_FROM = 'from'
SECTION_TO_NAME = 'TO'
IMAP_TO = 'to'
DEFAULT_CONFIG_PATH = '../config/imap-manager.conf'
ENCODING = 'utf8'

def get_folder(config, rule, param):
    folder = ''
    # Check if the mail has a rule
    for argument, value in list(config.items(rule)):
        # Remove the quotes
        argument = argument[1:-1]
        if argument.lower() in param.lower():
            folder = value
            break

    return folder

def get_default_folder(config):
    # Get the default folder in the config file
    return config.get(SECTION_GENERAL_NAME, IMAP_DEFAULT_FOLDER_NAME)

def clean_address(address):
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
    if sys.version_info <= (3, 7):
        my_logger.log(ERROR, 'The script needs at least python 3.7')
        sys.exit(1)
