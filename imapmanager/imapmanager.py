#!/usr/bin/env python3

"""
imapmanager.py: imapmanager's main file.

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


import logging
from signal import signal, strsignal, SIGINT, SIGTERM
from time import sleep

from imap import Imap
from utils import *  # TODO


running = True

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s: %(message)s",
)
logger = logging.getLogger("imapmanager")


def signal_handler(signal_value, _frame):
    """
    Function to treat signals catched.
    If a signal is catched, <running> is set to False and the main loop will exit soon.
    :param  signal_value        the value of the signal catched
    :param  frame               unused (needed because of the signal API)
    """
    global running
    logger.info("Signal %s catched, stopping...", strsignal(signal_value))
    running = False


def main():
    logger.info("Starting imapmanager...")

    # INIT
    signal(SIGINT, signal_handler)
    signal(SIGTERM, signal_handler)

    config, config_path = open_and_load_config()

    level = logging.getLevelName(
        config.get(SECTION_GENERAL_NAME, LOG_LEVEL)
    )
    logger.setLevel(level)

    # Get some parameters for easier convenience
    hostname = config.get(SECTION_GENERAL_NAME, HOSTNAME_NAME)
    port = config.get(SECTION_GENERAL_NAME, PORT_NAME)
    username = config.get(SECTION_GENERAL_NAME, USERNAME_NAME)
    password = config.get(SECTION_GENERAL_NAME, PASSWORD_NAME)
    mailbox = config.get(SECTION_GENERAL_NAME, MAILBOX_NAME)
    polling_interval = config.get(
        SECTION_GENERAL_NAME, POLLING_INTERVAL_NAME
    )

    logger.info(
        "imapmanager initialized with on %s with %s using %s",
        hostname,
        username,
        config_path,
    )

    imap = Imap(logger, hostname, port, username, password, mailbox, config)

    # MAIN LOOP
    while running:
        imap.maybe_reconnect()
        imap.process_mails()
        # If signal occurs during process, there is no need to sleep
        if running:
            sleep(float(polling_interval))

    # ENDING
    imap.logout()
    logger.info("imapmanager closed.")


if __name__ == "__main__":
    main()
