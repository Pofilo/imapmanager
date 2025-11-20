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
HOSTNAME_NAME = "hostname"
PORT_NAME = "port"
USERNAME_NAME = "username"
PASSWORD_NAME = "password"  # noqa: S105 (hardcoded-password-string)
MAILBOX_NAME = "mailbox"
POLLING_INTERVAL_NAME = "pollingInterval"
IMAP_DEFAULT_FOLDER_NAME = "defaulFolder"
LOG_LEVEL_NAME = "logLevel"

SECTION_FILTERS_NAME = "filters"
SECTION_SUBJECT_NAME = "subject"
SECTION_BODY_NAME = "body"
SECTION_FROM_NAME = "from"
SECTION_DEST_NAME = "dest"

SECTION_TELEGRAM_NAME = "telegram"
TELEGRAM_TOKEN_NAME = "token"  # noqa: S105 (hardcoded-password-string)
TELEGRAM_CHAT_ID_NAME = "chat_id"

# IMAP VARIABLES
IMAP_SUBJECT = "subject"
IMAP_BODY = "body"
IMAP_FROM = "from"
IMAP_TO = "to"
IMAP_CC = "cc"

# DEFAULT VARIABLES
DEFAULT_CONFIG_PATH = "/etc/imapmanager.conf.yml"
ENCODING = "utf-8"
