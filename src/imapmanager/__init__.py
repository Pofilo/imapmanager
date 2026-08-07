"""
__init__.py: imapmanager's main file.

imapmanager: Connect and manage your mail account through IMAP.
Copyright (C) pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms
of the GNU General Public License as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import logging
from signal import SIGINT, SIGTERM, signal, strsignal
from sys import exit as sys_exit
from threading import Event
from typing import TYPE_CHECKING

from imapmanager.conf import ImapConf
from imapmanager.constants import (
    EXIT_FATAL,
    EXIT_OK,
    HEARTBEAT_GRACE,
    LOG_LEVEL_NAME,
    POLLING_INTERVAL_NAME,
)
from imapmanager.heartbeat import Heartbeat
from imapmanager.imap import Imap

if TYPE_CHECKING:
    from types import FrameType

stop_event = Event()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s: %(message)s",
)
logger = logging.getLogger("imapmanager")


def signal_handler(signal_value: int, _frame: FrameType) -> None:
    """
    Treat signals caught.
    If a signal is caught, <running> is set to False and the main loop will exit soon.
    :param  signal_value        the value of the signal caught
    :param  frame               unused (needed because of the signal API).
    """
    logger.info("Signal %s caught, stopping...", strsignal(signal_value))
    stop_event.set()


def main() -> int:
    """
    Start the imapmanager and remain in the while loop.
    :return     <EXIT_FATAL> when the daemon died on its own, <EXIT_OK> otherwise.
    """
    logger.info("Starting imapmanager...")

    # INIT
    signal(SIGINT, signal_handler)
    signal(SIGTERM, signal_handler)
    config = ImapConf(logger=logger)
    log_level = logging.getLevelName(config.get(LOG_LEVEL_NAME))
    logger.setLevel(log_level)

    for module in ("requests",):
        logging.getLogger(module).setLevel(max(log_level, logging.INFO))

    # Pin urllib3 loggers to at least INFO: at DEBUG, it logs the full request URL,
    # leaking any notifier credential carried by the URL (such as the Telegram bot
    # token, which sits in the path) into the logs.
    logging.getLogger("urllib3").setLevel(max(log_level, logging.INFO))

    polling_interval = config.get(POLLING_INTERVAL_NAME)

    # Publish a first heartbeat before creating Imap() (which does a connection).
    heartbeat = Heartbeat(valid_for=float(polling_interval) + HEARTBEAT_GRACE)
    heartbeat.refresh()

    imap = Imap(logger, config, stop_event, heartbeat)

    # MAIN LOOP
    while not stop_event.is_set():
        try:
            imap.process_mails(stop_event)
        except Exception:
            # Should never happen, log the traceback for further digging.
            logger.exception("Unexpected error during process_mails, continuing...")

        # Maybe the imap process needs to stop
        if not imap.running:
            logger.info("imap process not running, stopping...")
            stop_event.set()

        heartbeat.refresh()

        stop_event.wait(timeout=float(polling_interval))

    # ENDING
    imap.logout()

    if imap.fatal:
        logger.critical("imapmanager closed after a fatal error.")
        return EXIT_FATAL

    logger.info("imapmanager closed.")
    return EXIT_OK


if __name__ == "__main__":
    sys_exit(main())
