"""
__init__.py: imapmanager's main file.

imapmanager: Connect and manage your mail account through IMAP.
Copyright (C) pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms
of the GNU General Public License as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANYWARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import logging
from signal import SIGINT, SIGTERM, signal, strsignal
from time import sleep
from types import FrameType

from imapmanager.conf import ImapConf
from imapmanager.constants import (
    LOG_LEVEL_NAME,
    POLLING_INTERVAL_NAME,
)
from imapmanager.imap import Imap

main_running = True

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s: %(message)s",
)
logger = logging.getLogger("imapmanager")


def signal_handler(signal_value: int, _frame: FrameType) -> None:
    """
    Treat signals catched.
    If a signal is catched, <running> is set to False and the main loop will exit soon.
    :param  signal_value        the value of the signal catched
    :param  frame               unused (needed because of the signal API).
    """
    global main_running  # noqa: PLW0603 (global-statement)
    logger.info("Signal %s catched, stopping...", strsignal(signal_value))
    main_running = False


def main() -> None:
    """
    Start the imapmanager and remain in the while loop.
    """
    global main_running  # noqa: PLW0603 (global-statement)
    logger.info("Starting imapmanager...")

    # INIT
    signal(SIGINT, signal_handler)
    signal(SIGTERM, signal_handler)
    config = ImapConf(logger=logger)
    log_level = logging.getLevelName(config.get(LOG_LEVEL_NAME))
    logger.setLevel(log_level)

    for module in ("requests", "urllib3"):
        logging.getLogger(module).setLevel(log_level)

    imap = Imap(logger, config)

    polling_interval = config.get(POLLING_INTERVAL_NAME)

    # MAIN LOOP
    while main_running:
        imap.process_mails()

        # Maybe the imap process needs to stop
        if not imap.running:
            logger.info("imap process not running, stopping...")
            main_running = False

        # If signal occurs during process, there is no need to sleep
        if main_running:
            sleep(float(polling_interval))

    # ENDING
    imap.logout()
    logger.info("imapmanager closed.")


if __name__ == "__main__":
    main()
