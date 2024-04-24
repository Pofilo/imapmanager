"""
constants.py: all constants used by imapmanager.

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

# CONFIGURATION VARIABLES NAMES
CONFIG_PATH_NAME = "IMAPMANAGER_CONFIG_PATH"
SECTION_GENERAL_NAME = "GENERAL"
HOSTNAME_NAME = "IMAP_HOSTNAME"
PORT_NAME = "IMAP_PORT"
USERNAME_NAME = "IMAP_USERNAME"
PASSWORD_NAME = "IMAP_PASSWORD"
MAILBOX_NAME = "IMAP_MAILBOX"
POLLING_INTERVAL_NAME = "POLLING_INTERVAL"
IMAP_DEFAULT_FOLDER_NAME = "DEFAULT_FOLDER"
LOG_LEVEL_NAME = "LOG_LEVEL"
SECTION_SUBJECT_NAME = "SUBJECT"
SECTION_FROM_NAME = "FROM"
SECTION_DEST_NAME = "DEST"

# IMAP VARIABLES
IMAP_SUBJECT = "subject"
IMAP_FROM = "from"
IMAP_TO = "to"
IMAP_CC = "cc"

# DEFAULT VARIABLES
DEFAULT_CONFIG_PATH = "/etc/imapmanager.conf"
ENCODING = "utf-8"
