#!/usr/bin/env python3

"""
list_folders.py: utility script to list all folders in a mailbox.

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

import argparse
import logging
from imaplib import IMAP4_SSL


def list_folders(
    hostname: str, port: int, username: str, password: str, logger: logging.Logger
) -> None:
    """
    Connect to the mailbox and list all folders.
    """
    try:
        with IMAP4_SSL(hostname, port) as mail:
            mail.login(username, password)
            logger.info("Successful connection as username=%s", username)
            status, folders = mail.list()
            if status == "OK":
                for folder in folders:
                    logger.info(folder.decode())
            else:
                logger.error("Failed to list folders.")
    except Exception:
        logger.exception("An error occurred")


def parse_args() -> argparse.Namespace:
    """
    Parse arguments given to the script.
    """
    parser = argparse.ArgumentParser(description="List IMAP mailboxes.")
    parser.add_argument("hostname", help="IMAP server address")
    parser.add_argument("username", help="Email address")
    parser.add_argument("password", help="Email password")
    parser.add_argument(
        "--port", type=int, default=993, help="IMAP server port (default: 993)"
    )

    return parser.parse_args()


def main() -> None:
    """
    Configure logger and list all folders of the mailbox.
    """
    # Configure logger
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s: %(message)s",
    )
    logger = logging.getLogger("list-folders")

    args = parse_args()
    list_folders(args.hostname, args.port, args.username, args.password, logger)


if __name__ == "__main__":
    main()
