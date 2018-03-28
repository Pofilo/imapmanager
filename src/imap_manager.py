'''
imap_manager.py: imap-manager's main file.

imap-manager: Connect and manage your mail account through IMAP.
Copyright (C) 2016-2018 pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.

'''


import imaplib
import sys, signal, time
import ConfigParser
from time import sleep

import imap
import utils
from logger import log, ERROR, WARN, INFO, DEBUG

running = True

def signalHandler(signal, frame):
	global running
	running = False

signal.signal(signal.SIGINT, signalHandler)
signal.signal(signal.SIGTERM, signalHandler)

# Open and load the config file
config = ConfigParser.ConfigParser()
config.read(utils.defaultConfigPath)

hostname = config.get(utils.sectionDefault, utils.hostname)
port = config.get(utils.sectionDefault, utils.port)
username = config.get(utils.sectionDefault, utils.username)
password = config.get(utils.sectionDefault, utils.password)
mailbox = config.get(utils.sectionDefault, utils.mailbox)
pollingInterval = config.get(utils.sectionDefault, utils.pollingInterval)

log(INFO, '--------------------')
log(INFO, 'imap-manager initialized with on "{}" with "{}"'.format(hostname, username))

m = imap.connect(hostname, port, username, password)
m.select(mailbox)

while running:
	if(not imap.check(m)):
		log(WARN, 'Check connection failed, trying to reconnect ...')
		m = imap.connect(hostname, port, username, password)
	data = imap.processMails(config, m)
	# If signal occurs during process, there is no need to sleep
	if running:
		time.sleep(float(pollingInterval))

imap.logout(m)
log(INFO, 'imap-manager closed.')
