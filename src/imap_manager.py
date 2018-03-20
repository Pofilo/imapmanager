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
username = config.get(utils.sectionDefault, utils.username)
password = config.get(utils.sectionDefault, utils.password)
mailbox = config.get(utils.sectionDefault, utils.mailbox)
pollingInterval = config.get(utils.sectionDefault, utils.pollingInterval)

utils.log(utils.INFO, '--------------------')
utils.log(utils.INFO, 'imap-manager initialized with on "{}" with "{}"'.format(hostname, username))

m = imap.connect(hostname, username, password)
m.select(mailbox)

while running:
	if(not imap.check(m)):
		utils.log(utils.INFO, 'Check connection failed, trying to reconnect ...')
		m = imap.connect(hostname, username, password)
	data = imap.processMails(config, m)
	# If signal occurs during process, there is no need to sleep
	if running:
		time.sleep(float(pollingInterval))

imap.logout(m)
utils.log(utils.INFO, 'imap-manager closed.')


