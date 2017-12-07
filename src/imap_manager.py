import imaplib
import sys
import yaml
from time import sleep

import imap
import utils

#reload(sys)
#sys.setdefaultencoding('utf8')

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

while 1:
	if(not imap.check(m)):
		utils.log(utils.INFO, 'Check connection failed, trying to reconnect ...')
		m = imap.connect(username, password, imapServer)
	data = imap.processMails(conf, m)
	sleep(sleepDuration)
	
imap.logout(m)

utils.log(utils.INFO, 'imap-manager closed.')

