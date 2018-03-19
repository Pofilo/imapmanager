import imaplib
import sys, signal, time
import yaml
from time import sleep

import imap
import utils

running = True

def signalHandler(signal, frame):
	global running
	running = False

signal.signal(signal.SIGINT, signalHandler)
signal.signal(signal.SIGTERM, signalHandler)

confFile = utils.defaultConfigPath
# Open and load the file conf
conf = yaml.load(open(confFile, 'r'))

username = conf[utils.username]
password = conf[utils.password]
imapServer = conf[utils.imapServer]
directory = conf[utils.directory]
sleepDuration = conf[utils.sleepDuration]

utils.log(utils.INFO, '--------------------')
utils.log(utils.INFO, 'imap-manager launched with user "{}" on "{}"'.format(username, imapServer))

m = imap.connect(username, password, imapServer)
m.select(conf[utils.directory])

while running:
	if(not imap.check(m)):
		utils.log(utils.INFO, 'Check connection failed, trying to reconnect ...')
		m = imap.connect(username, password, imapServer)
	data = imap.processMails(conf, m)
	# If signal occurs during process, there is no need to sleep
	if running:
		time.sleep(sleepDuration)

imap.logout(m)
utils.log(utils.INFO, 'imap-manager closed.')


