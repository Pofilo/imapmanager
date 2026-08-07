# IMAP Manager
Last stable version [available here](https://git.pofilo.fr/pofilo/imapmanager/tags).

Connect and manage your emails through IMAP over SSL.

## Requirements

+ The script uses **python 3.14.6**
+ Dependencies listed in `pyproject.toml`

## Purpose

The first objective is to **automatically sort your mail** into the desired folder. You can add optional rules on those fields, for now:
- **subject**
- **body**
- **from**
- **dest** (including **to** and **cc**)

## Actions

If a mail matches with a filter, some actions can be taken.
List of supported actions:
- `mark_as_read`: mark the mail as already read (this action is optional)
- `move`: move the mail into the desired folder (this action is mandatory)
- `pushover`: send a pushover notification (this action is optional)
- `telegram`: send a telegram notification (this action is optional)

Note that the pushover notification requires setting up a token and user_key.
You can [find here](https://git.pofilo.fr/pofilo/imapmanager/src/branch/master/doc/notice-pushover.md) the documentation helping you to set up the pushover configuration.

Note that the telegram notification requires setting up a token and chat_id.
You can [find here](https://git.pofilo.fr/pofilo/imapmanager/src/branch/master/doc/notice-telegram.md) the documentation helping you to set up the telegram configuration.

## Installation

### Manual with a virtual environment

+ Download the last stable version [available here](https://git.pofilo.fr/pofilo/imapmanager/tags)
+ `cd imapmanager`
+ Create virtual environment: `python3.14.6 -m venv venv`
+ Source it: `source venv/bin/activate`
+ Install `uv`: `pip install uv`
+ Install dependencies: `uv pip install .`
+ `cp config/imapmanager.sample.conf.yml /etc/imapmanager.conf.yml`
+ Edit `/etc/imapmanager.conf.yml`
+ `imapmanager`

You can change the path of the configuration file and set the environment variable `export IMAPMANAGER_CONFIG_PATH="config/imapmanager.conf.yml"`

Folders of a mailbox can be listed by using the script `list-folders`.

### Using Docker

+ Create the configuration file using the [template available here](https://git.pofilo.fr/pofilo/imapmanager/src/branch/master/config/imapmanager.sample.conf.yml) (use the template corresponding to the version of **imapmanager** you will be using).
+ `docker run -ti --restart=on-failure:3 -v $(pwd)/config/imapmanager.conf.yml:/etc/imapmanager.conf.yml pofilo:imapmanager:<last_tag>`

The image ships a native healthcheck.
**imapmanager** refreshes a heartbeat file while it makes progress, so the container turns `unhealthy` only when the process is alive but stuck.
Note that Docker does not auto restart or whatever when the container is `unhealthy`.

### Options

+ `IMAPMANAGER_CONFIG_PATH` *(optional)*
    + Specify the path of the configuration file.
    + Default value is `/etc/imapmanager.conf.yml`.
+ `IMAPMANAGER_HEARTBEAT_PATH` *(optional)*
    + Specify the path of the heartbeat file used by the healthcheck.
    + Unset means no heartbeat file is written at all.
    + By default, the Docker image sets it to `/run/imapmanager.heartbeat`.

## Development

Install "pre-commit" hook: `ln -s $(pwd)/hook-pre-commit .git/hooks/pre-commit`.
Linters and typos will be checked before committing.

### Tests

+ Install dependencies: `pip install .[tests]`
+ Run tests: `pytest`
+ Run tests with coverage: `pytest --cov`
+ Optional HTML report in `htmlcov/`: `pytest --cov --cov-report=html`

### Linters

+ Install dependencies: `pip install .[linters]`
+ Run linters:

```bash
ruff format --diff
ruff check
```

### Typos

+ Install [typos](https://github.com/crate-ci/typos)
+ Run it: `typos`

## License

This project is licensed under the GNU GPL License. See the [LICENSE](https://git.pofilo.fr/pofilo/imapmanager/src/branch/master/LICENSE) file for the full license text.

## Bugs

If you experience an issue, have other ideas for the development, or anything else, feel free to [report it](https://git.pofilo.fr/pofilo/imapmanager/issues) or [fix it with a PR](https://git.pofilo.fr/pofilo/imapmanager/pulls)!
