import imaplib

from imap import connect, logout, processMails

confFile = "config.yaml"
mail = connect(confFile)
data = processMails(confFile, mail)
logout(mail)
