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
import ConfigParser
import os.path
from time import sleep

import imap
import utils, confUtils
from logger import log, ERROR, WARN, INFO, DEBUG

running = True

def signalHandler(signal, frame):
	global running
	running = False

def openAndLoadConfig(args):
	if args.configPath:
		configPath = args.configPath
	else:
		configPath = utils.defaultConfigPath
	config = ConfigParser.SafeConfigParser()

	if os.path.isfile(configPath):
		try:
			config.read(configPath)
		except ConfigParser.ParsingError as e:
			log(ERROR, 'Parsing error: {}'.format(str(e)))
			sys.exit(1)
	else:
		log(ERROR, 'Config file "{}" not found."'.format(configPath))
		sys.exit(1)

	confUtils.checkConfig(config)

	return config, configPath

def main():
	log(INFO, '--------------------')

	signal.signal(signal.SIGINT, signalHandler)
	signal.signal(signal.SIGTERM, signalHandler)

	# Parse arguments
	parser = argparse.ArgumentParser()
	parser.add_argument('--conf', '-c', dest='configPath')
	args = parser.parse_args()

	# Open conf and load parameters
	config, configPath = openAndLoadConfig(args)
	hostname = config.get(utils.sectionDefault, utils.hostname)
	port = config.get(utils.sectionDefault, utils.port)
	username = config.get(utils.sectionDefault, utils.username)
	password = config.get(utils.sectionDefault, utils.password)
	mailbox = config.get(utils.sectionDefault, utils.mailbox)
	pollingInterval = config.get(utils.sectionDefault, utils.pollingInterval)

	log(INFO, 'imap-manager initialized with on "{}" with "{}" using "{}"'.format(hostname, username, configPath))

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

if __name__ == '__main__':
	main()
