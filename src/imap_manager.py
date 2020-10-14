'''
imap_manager.py: imap-manager's main file.

imap-manager: Connect and manage your mail account through IMAP.
Copyright (C) 2016-2018 pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.

'''


import argparse
import imaplib
import sys, signal, time
import configparser
import os.path
from time import sleep

import imap
import utils, confUtils
from logger import Logger, FATAL, ERROR, WARN, INFO, DEBUG

running = True
my_logger = Logger()

def signal_handler(signal, frame):
    global running
    running = False

def open_and_load_config(args):
    if args.config_path:
        config_path = args.config_path
    else:
        config_path = utils.DEFAULT_CONFIG_PATH
    config = configparser.ConfigParser()

    if os.path.isfile(config_path):
        try:
            config.read(config_path)
        except configparser.ParsingError as e:
            my_logger.log(ERROR, 'Parsing error: {}'.format(str(e)))
            sys.exit(1)
    else:
        my_logger.log(ERROR, 'Config file "{}" not found."'.format(config_path))
        sys.exit(1)

    confUtils.check_config(config)

    return config, config_path

def main():
    my_logger.log(INFO, '--------------------')

    # Check python version
    utils.check_python_version()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--conf', '-c', dest='config_path')
    args = parser.parse_args()

    # Open conf and load parameters
    config, config_path = open_and_load_config(args)
    my_logger.level_used = config.get(utils.SECTION_GENERAL_NAME, utils.LOG_LEVEL)
    hostname = config.get(utils.SECTION_GENERAL_NAME, utils.HOSTNAME_NAME)
    port = config.get(utils.SECTION_GENERAL_NAME, utils.PORT_NAME)
    username = config.get(utils.SECTION_GENERAL_NAME, utils.USERNAME_NAME)
    password = config.get(utils.SECTION_GENERAL_NAME, utils.PASSWORD_NAME)
    mailbox = config.get(utils.SECTION_GENERAL_NAME, utils.MAILBOX_NAME)
    polling_interval = config.get(utils.SECTION_GENERAL_NAME, utils.POLLING_INTERVAL_NAME)

    my_logger.log(INFO, 'imap-manager initialized with on "{}" with "{}" using "{}"'.format(hostname, username, config_path))

    m = imap.connect(hostname, port, username, password)
    m.select(mailbox)

    while running:
        if(not imap.check(m)):
            my_logger.log(WARN, 'Check connection failed, trying to reconnect ...')
            m = imap.connect(hostname, port, username, password)
        data = imap.process_mails(config, m)
        # If signal occurs during process, there is no need to sleep
        if running:
            time.sleep(float(polling_interval))

    imap.logout(m)
    my_logger.log(INFO, 'imap-manager closed.')

if __name__ == '__main__':
    main()

