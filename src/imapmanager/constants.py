"""
constants.py: all constants used by imapmanager.

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

# CONFIGURATION VARIABLES NAMES
CONFIG_PATH_NAME = "IMAPMANAGER_CONFIG_PATH"
HOSTNAME_NAME = "hostname"
PORT_NAME = "port"
USERNAME_NAME = "username"
PASSWORD_NAME = "password"  # noqa: S105 (hardcoded-password-string)
MAILBOX_NAME = "mailbox"
POLLING_INTERVAL_NAME = "pollingInterval"
IMAP_DEFAULT_FOLDER_NAME = "defaultFolder"
LOG_LEVEL_NAME = "logLevel"
WEIGHT_NAME = "weight"

SECTION_FILTERS_NAME = "filters"
SECTION_SUBJECT_NAME = "subject"
SECTION_BODY_NAME = "body"
SECTION_FROM_NAME = "from"
SECTION_DEST_NAME = "dest"

FILTER_PATTERN_NAME = "pattern"
FILTER_ACTIONS_NAME = "actions"
FILTER_WEIGHT_NAME = WEIGHT_NAME

FILTER_ACTION_MARK_AS_READ_NAME = "mark_as_read"
FILTER_ACTION_MOVE_NAME = "move"
FILTER_ACTION_TELEGRAM_NAME = "telegram"
FILTER_ACTION_PUSHOVER_NAME = "pushover"

SECTION_TELEGRAM_NAME = "telegram"
TELEGRAM_TOKEN_NAME = "token"  # noqa: S105 (hardcoded-password-string)
TELEGRAM_CHAT_ID_NAME = "chat_id"

SECTION_PUSHOVER_NAME = "pushover"
PUSHOVER_TOKEN_NAME = "token"  # noqa: S105 (hardcoded-password-string)
PUSHOVER_USER_KEY_NAME = "user_key"

# Notification actions: action name -> (config section, mandatory credential keys).
# A section absent (or explicitly empty) means the notifier is disabled.
NOTIFIERS = {
    FILTER_ACTION_PUSHOVER_NAME: (
        SECTION_PUSHOVER_NAME,
        (PUSHOVER_TOKEN_NAME, PUSHOVER_USER_KEY_NAME),
    ),
    FILTER_ACTION_TELEGRAM_NAME: (
        SECTION_TELEGRAM_NAME,
        (TELEGRAM_TOKEN_NAME, TELEGRAM_CHAT_ID_NAME),
    ),
}

# IMAP VARIABLES
IMAP_SUBJECT = "subject"
IMAP_BODY = "body"
IMAP_FROM = "from"
IMAP_TO = "to"
IMAP_CC = "cc"

# DEFAULT VARIABLES
DEFAULT_CONFIG_PATH = "/etc/imapmanager.conf.yml"
ENCODING = "utf-8"
DEFAULT_WEIGHT = 0
