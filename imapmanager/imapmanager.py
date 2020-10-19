#!/usr/bin/env python3

'''
imapmanager.py: imapmanager's main file.

imapmanager: Connect and manage your mail account through IMAP.
Copyright (C) 2016-2020 pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.

'''


import logging
import imaplib
import sys, signal, time
from time import sleep

import imap
import utils

### GLOBAL VARIABLES ###
running = True

### LOGGING CONF ###
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s: %(message)s'
)
logger = logging.getLogger('imapmanager')

### FUNCTIONS ###

def signal_handler(signal_value, frame):
    """
    Function to treat signals catched.
    If a signal is catched, <running> is set to False and the main loop will exit soon.
    :param  signal_value        the value of the signal catched
    :param  frame               unused (needed because of the signal API)
    """
    global running
    # TODO: strsignal will be available in python 3.8
    # logger.debug("Signal {} catched, stopping...".format(signal.strsignal(signal_value)))
    logger.debug("Signal {} catched, stopping...".format(signal_value))
    running = False

def main():
    logger.info('Starting imapmanager...')

    ### INIT ###

    # Check python version
    utils.check_python_version()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    config, config_path = utils.open_and_load_config()

    level = logging.getLevelName(config.get(utils.SECTION_GENERAL_NAME, utils.LOG_LEVEL))
    logger.setLevel(level)

    # Get some parameters for easier convenience
    hostname = config.get(utils.SECTION_GENERAL_NAME, utils.HOSTNAME_NAME)
    port = config.get(utils.SECTION_GENERAL_NAME, utils.PORT_NAME)
    username = config.get(utils.SECTION_GENERAL_NAME, utils.USERNAME_NAME)
    password = config.get(utils.SECTION_GENERAL_NAME, utils.PASSWORD_NAME)
    mailbox = config.get(utils.SECTION_GENERAL_NAME, utils.MAILBOX_NAME)
    polling_interval = config.get(utils.SECTION_GENERAL_NAME, utils.POLLING_INTERVAL_NAME)

    logger.info('imapmanager initialized with on "{}" with "{}" using "{}"'.format(hostname, username, config_path))

    mail_handler = imap.connect(hostname, port, username, password)
    mail_handler.select(mailbox)

    ### MAIN LOOP ###

    while running:
        if(not imap.check_connection(mail_handler)):
            logger.warn('Check connection failed, trying to reconnect ...')
            mail_handler = imap.connect(hostname, port, username, password)
        imap.process_mails(config, mail_handler)
        # If signal occurs during process, there is no need to sleep
        if running:
            time.sleep(float(polling_interval))

    ### ENDING ###
    imap.logout(mail_handler)
    logger.info('imapmanager closed.')

if __name__ == '__main__':
    main()

