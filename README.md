# imap-manager

Connect and manage your mail account through IMAP over SSL.

## Requirements

+ pip install pyyaml (may work without that on some platforms)

## Purpose

You want to automatically moove your mails into the good folder. However, the use here is a bit special. Consider a main mail address and some aliases that redirect to this address. The goal of this script is to redirect mails received for a special alias into the folder corresponding to that alias.

## Example

To use the script, you need to use this syntax: 
+ If you have the address *contact@pofilo.fr*, your folder will be named *@contact*.

I choose to add an *@* as a prefix to differenciate the folders (if a folder start by *@*, the folder corresponds to an alias).

## Installation

+ Wait a bit that the script is a bit more advanced
+ Copy *config.yaml.sample* into *config.yaml* and update the values
+ Execute the script *main.py*

## More

### TODO List

+ Finish the basic of the script to be functionnal (it's a bit obvious ^^)
+ Add the functionnality to send a sms for any mails of a specific alias
+ To be more general and allows to filter in function of the sender or with a regex on the subject of the mail

### Contact

If you experience an issue, you have other ideas to the developpement or anything else, please [report](https://git.pofilo.fr/pofilo/imap-manager/issues) them !
