# IMAP Manager
Last stable version [available here](https://git.pofilo.fr/pofilo/imapmanager/releases).

Connect and manage your emails through IMAP over SSL.

## Requirements

+ The script uses **python 3.7**
+ Dependencies listed in `requirements.txt`

## Purpose

The first objective is to **automatically sort your mails** into the desired folder. You can add rules on those fields for now:
- **subject**
- **from**
- Dest (including **to** and **cc**)

## Installation

### Manual with a virtual environment

+ Download the last stable version [available here](https://git.pofilo.fr/pofilo/imapmanager/releases)
+ `cd imapmanager`
+ Create virtual environment: `python3.7 -m venv .`
+ Source it: `source bin/activate`
+ Install dependencies: `pip install -r requirements.txt`
+ `cp config/imapmanager.sample.conf /etc/imapmanager.conf`
+ Edit */etc/imapmanager.conf*
+ `imapmanager/imapmanager.py`

You can change the path of the configuration file and set the environment variable `export IMAPMANAGER_CONFIG_PATH="config/imapmanager.conf"`

### Using Docker

+ Create the configuration file using the [template available here](https://git.pofilo.fr/pofilo/imapmanager/src/branch/master/config/imapmanager.sample.conf) (use the template corresponding to the version of **imapmanager** you will be using).
+ `docker run -ti -v $(pwd)/config/imapmanager.conf:/etc/imapmanager.conf pofilo:imapmanager:<last_tag>`

### Options

+ `IMAPMANAGER_CONFIG_PATH` *(optional)*
    + Specify the path of the configuration file
    + Default value is `/etc/imapmanager.conf`

## License

This project is licensed under the GNU GPL License. See the [LICENSE](https://git.pofilo.fr/pofilo/imapmanager/src/branch/master/LICENSE) file for the full license text.

## Bugs

If you experience an issue, you have other ideas for the development, or anything else, feel free to [report it](https://git.pofilo.fr/pofilo/imapmanager/issues) or [fix it with a PR](https://git.pofilo.fr/pofilo/imapmanager/pulls)!

