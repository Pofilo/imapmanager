# imap-manager
Version 0.1

Connect and manage your mail account through IMAP over SSL.

## Requirements

+ pip install pyyaml (may work without that on some platforms)

## Purpose

You want to automatically moove your mails into the good folder. However, the use here is a bit special. Consider a main mail address and some aliases that redirect to this address. The goal of this script is to redirect mails received for a special alias into the folder corresponding to that alias.

## Example

To use the script, you need to use the syntax presented in *config.yaml.sample* (care to not use tabulations but spaces). 
In the sample, the mail for *mail1@domain.com* will be moved in the folder named *folder1*.

## Installation

+ **I don't suggest you to use this script, data may be lost. It's more designed for my personal use.**
+ Wait a bit that the script is a bit more advanced
+ Copy *config.yaml.sample* into *config.yaml* and update the values
+ Execute the script *imap-manager.py* (you have to execute it placing yourself at the level of this file)

## More

### TODO List

+ Deal with mails not encoded in utf8
+ Add the functionnality to send a sms for any mails of a specific alias
+ To be more general and allows to filter in function of the sender or with a regex on the subject of the mail
+ Make a web interface for the configuration ?

### Contact

If you experience an issue, you have other ideas to the developpement or anything else, please [report](https://git.pofilo.fr/pofilo/imap-manager/issues) them !
