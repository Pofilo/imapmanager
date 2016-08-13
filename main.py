import imaplib

from imap import connect, logout, parseMail

confFile = "config.yaml"
mail = connect(confFile)
data = parseMail(confFile, mail)
logout(mail)
