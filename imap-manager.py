import imaplib

from imap import connect, logout, processMails
from time import sleep

confFile = "config.yaml"
while 1: 	
	mail = connect(confFile)
	data = processMails(confFile, mail)
	logout(mail)
	sleep(5)
