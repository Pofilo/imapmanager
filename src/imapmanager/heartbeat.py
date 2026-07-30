"""
heartbeat.py: publish the liveness deadline consumed by a healthcheck.

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
from os import environ
from pathlib import Path
from time import time

from imapmanager.constants import (
    ENCODING,
    HEARTBEAT_PATH_NAME,
)

logger = logging.getLogger("imapmanager")


class Heartbeat:
    """
    Publish the timestamp until which the daemon must be considered alive.
    Disabled unless a path is given through <HEARTBEAT_PATH_NAME> environment variable.
    """

    def __init__(self, valid_for: float) -> None:
        self._valid_for = valid_for
        path = environ.get(HEARTBEAT_PATH_NAME)
        self._path = Path(path) if path else None
        self._tmp_path = (
            self._path.with_name(self._path.name + ".tmp") if self._path else None
        )
        self._failed = False

        if not self._path:
            logger.debug("Heartbeat disabled: %s is not set", HEARTBEAT_PATH_NAME)

    def refresh(self, valid_for: float | None = None) -> None:
        """
        Push atomically the deadline back. Never raise: losing the heartbeat must not
        stop mails being processed.
        Do nothing when the heartbeat is disabled.
        :param      valid_for   seconds to stay alive for, default when omitted.
        """
        if not self._path:
            return

        deadline = int(time() + (self._valid_for if valid_for is None else valid_for))
        try:
            self._tmp_path.write_text(str(deadline), encoding=ENCODING)
            self._tmp_path.replace(self._path)
        except OSError as exc:
            # Only log the first failure of a streak.
            if not self._failed:
                logger.warning("Failed to write heartbeat=%s: err=%s", self._path, exc)
                self._failed = True
        else:
            if self._failed:
                logger.info("Heartbeat writable again: path=%s", self._path)
                self._failed = False
