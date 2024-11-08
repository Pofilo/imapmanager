# IMAP Manager
Last stable version [available here](https://git.pofilo.fr/pofilo/imapmanager/tags).

Connect and manage your emails through IMAP over SSL.

## Requirements

+ The script uses **python 3.12.7**
+ Dependencies listed in `pyproject.toml`

## Purpose

The first objective is to **automatically sort your mail** into the desired folder. You can add optional rules on those fields, for now:
- **subject**
- **from**
- **dest** (including **to** and **cc**)

## Actions

If a mail matches with a filter, some actions can be taken.
List of supported actions:
- `move`: move the mail into the desired folder (this action is mandatory)
- `telegram`: send a telegram notification (this action is optional)
- `mark_as_read`: mark the mail as already read (this action is optional)

Note that the telegram notification requires setting up a token and chat_id.
You can [find here](https://git.pofilo.fr/pofilo/imapmanager/src/branch/master/doc/notice-telegram.md) the documentation helping you to set up the telegram configuration.

## Installation

### Manual with a virtual environment

+ Download the last stable version [available here](https://git.pofilo.fr/pofilo/imapmanager/tags)
+ `cd imapmanager`
+ Create virtual environment: `python3.12.7 -m venv venv`
+ Source it: `source venv/bin/activate`
+ Install dependencies: `pip install .`
+ `cp config/imapmanager.sample.conf.yml /etc/imapmanager.conf.yml`
+ Edit `/etc/imapmanager.conf.yml`
+ `imapmanager`

You can change the path of the configuration file and set the environment variable `export IMAPMANAGER_CONFIG_PATH="config/imapmanager.conf.yml"`

### Using Docker

+ Create the configuration file using the [template available here](https://git.pofilo.fr/pofilo/imapmanager/src/branch/master/config/imapmanager.sample.conf.yml) (use the template corresponding to the version of **imapmanager** you will be using).
+ `docker run -ti -v $(pwd)/config/imapmanager.conf.yml:/etc/imapmanager.conf.yml pofilo:imapmanager:<last_tag>`

### Options

+ `IMAPMANAGER_CONFIG_PATH` *(optional)*
    + Specify the path of the configuration file
    + Default value is `/etc/imapmanager.conf.yml`

## Development

+ Install dependencies: `pip install .[linters]`
+ Run linters:

```
black --check --diff --quiet "src/imapmanager"
flake8 --max-line-length 88 "src/imapmanager"
pylint --rcfile=.pylintrc "src/imapmanager"
```

+ Install "pre-commit" hook: `ln -s $(pwd)/hook-pre-commit .git/hooks/pre-commit`

## License

This project is licensed under the GNU GPL License. See the [LICENSE](https://git.pofilo.fr/pofilo/imapmanager/src/branch/master/LICENSE) file for the full license text.

## Bugs

If you experience an issue, have other ideas for the development, or anything else, feel free to [report it](https://git.pofilo.fr/pofilo/imapmanager/issues) or [fix it with a PR](https://git.pofilo.fr/pofilo/imapmanager/pulls)!
