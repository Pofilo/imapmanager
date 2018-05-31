# imap-manager
Last stable version [available here](https://git.pofilo.fr/pofilo/imap-manager/releases).

Connect and manage your emails through IMAP over SSL.

## Requirements

+ None for the moment

## Purpose

The first objective is to **automatically sort your mails** into the desired folder. You can add rules on those fields for now:
- Subject
- From
- To

## Installation

+ `git clone https://git.pofilo.fr/pofilo/imap-manager.git`
+ `cd imap-manager`
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

If you experience an issue, you have other ideas to the developpement or anything else, feel free to [report](https://git.pofilo.fr/pofilo/imap-manager/issues) them !
