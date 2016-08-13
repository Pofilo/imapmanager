import imaplib

from imap import connect, logout, getMail

confFile = "config.yaml"
mail = connect(confFile)
data = getMail(confFile, mail)
logout(mail)
