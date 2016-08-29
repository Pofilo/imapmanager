import imaplib
import sys

from imap import connect, logout, processMails
from time import sleep

reload(sys)
sys.setdefaultencoding('utf8')
confFile = "config.yaml"
while 1: 	
	mail = connect(confFile)
	data = processMails(confFile, mail)
	logout(mail)
	sleep(5)
