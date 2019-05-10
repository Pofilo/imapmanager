# imap-manager
Last stable version [available here](https://git.pofilo.fr/pofilo/imap-manager/releases).

Connect and manage your emails through IMAP over SSL.

## Requirements

+ The script uses **python 3.7**
+ Dependencies listed in `requirements.txt`

## Purpose

The first objective is to **automatically sort your mails** into the desired folder. You can add rules on those fields for now:
- Subject
- From
- To

## Installation

+ Download the last stable version [available here](https://git.pofilo.fr/pofilo/imap-manager/releases)
+ `cd imap-manager`
+ Create virtual environment: `python3.7 -m venv .`
+ Source it: `source bin/activate`
+ Install dependencies: `pip install -r requirements.txt`
+ `cp config/imap-manager.sample.conf config/imap-manager.conf`
+ Edit *config/imap-manager.conf*
+ `cd src`
+ `python imap_manager.py`

### Options

+ `-c`, `--conf`
    + Specify the path of the configuration file (relative to `imap-manager/src` or absolute)
    + Default value is `../config/imap-manager.conf`

## License

This project is licensed under the GNU GPL License. See the [LICENSE](https://git.pofilo.fr/pofilo/imap-manager/src/branch/master/LICENSE) file for the full license text.

## Bugs

If you experience an issue, you have other ideas to the developpement or anything else, feel free to [report it](https://git.pofilo.fr/pofilo/imap-manager/issues) or [fix it with a PR](https://git.pofilo.fr/pofilo/imap-manager/pulls)!
