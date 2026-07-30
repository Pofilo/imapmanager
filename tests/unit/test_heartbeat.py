"""
Unit tests for imapmanager.heartbeat.Heartbeat.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time
from unittest import mock

from imapmanager.constants import HEARTBEAT_PATH_NAME
from imapmanager.heartbeat import Heartbeat


class TestHeartbeat(unittest.TestCase):
    def setUp(self) -> None:
        tmp_dir = TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.dir = Path(tmp_dir.name)
        self.path = self.dir / "beat"

    def make_heartbeat(self, path, valid_for=60):
        """
        Build a Heartbeat with <HEARTBEAT_PATH_NAME> set to <path>.
        The variable is read at build time only, hence the scoped patch.
        """
        with mock.patch.dict("os.environ", {HEARTBEAT_PATH_NAME: str(path)}):
            return Heartbeat(valid_for=valid_for)

    def make_disabled_heartbeat(self, valid_for=60):
        """
        Build a Heartbeat with <HEARTBEAT_PATH_NAME> unset.
        """
        with mock.patch.dict("os.environ", {}, clear=True):
            return Heartbeat(valid_for=valid_for)

    def read(self) -> int:
        return int(self.path.read_text(encoding="utf-8"))

    def test_refresh_writes_default_deadline(self) -> None:
        # The deadline is truncated to a whole second, so bound it the same way.
        before = time()
        self.make_heartbeat(self.path).refresh()
        assert int(before + 60) <= self.read() <= int(time() + 60)

    def test_explicit_valid_for_overrides_default(self) -> None:
        before = time()
        self.make_heartbeat(self.path).refresh(valid_for=600)
        assert int(before + 600) <= self.read() <= int(time() + 600)

    def test_no_temporary_file_left_behind(self) -> None:
        # The deadline must land through an atomic rename, never a partial write.
        self.make_heartbeat(self.path).refresh()
        assert [entry.name for entry in self.dir.iterdir()] == ["beat"]

    def test_repeated_refresh_overwrites(self) -> None:
        heartbeat = self.make_heartbeat(self.path)
        heartbeat.refresh()
        first = self.read()
        heartbeat.refresh(valid_for=3600)
        assert self.read() > first

    def test_path_read_once_at_build_time(self) -> None:
        # Moving the variable afterwards must not move an existing heartbeat.
        heartbeat = self.make_heartbeat(self.path)
        moved = self.dir / "moved"
        with mock.patch.dict("os.environ", {HEARTBEAT_PATH_NAME: str(moved)}):
            heartbeat.refresh()
        assert self.path.exists()
        assert not moved.exists()

    def test_unwritable_path_does_not_raise_and_warns_once(self) -> None:
        # Losing the heartbeat degrades the healthcheck; it must not stop the
        # daemon, nor log the same failure every polling interval.
        heartbeat = self.make_heartbeat(self.dir / "missing" / "beat")
        with mock.patch("imapmanager.heartbeat.logger") as logger:
            for _ in range(3):
                heartbeat.refresh()
        assert logger.warning.call_count == 1

    def test_recovery_after_failure_is_logged_and_rearms(self) -> None:
        heartbeat = self.make_heartbeat(self.dir / "missing" / "beat")
        with mock.patch("imapmanager.heartbeat.logger") as logger:
            heartbeat.refresh()
            (self.dir / "missing").mkdir()
            heartbeat.refresh()
            assert logger.info.call_count == 1
            # Re-armed: a second streak warns again instead of staying silent.
            (self.dir / "missing" / "beat").unlink()
            (self.dir / "missing").rmdir()
            heartbeat.refresh()
        assert logger.warning.call_count == 2

    def test_disabled_without_environment_variable(self) -> None:
        # No variable means no heartbeat: refresh must be a silent no-op.
        heartbeat = self.make_disabled_heartbeat()
        with mock.patch("imapmanager.heartbeat.logger") as logger:
            heartbeat.refresh()
            heartbeat.refresh(valid_for=600)
        assert list(self.dir.iterdir()) == []
        logger.warning.assert_not_called()
        logger.exception.assert_not_called()

    def test_empty_environment_variable_disables_heartbeat(self) -> None:
        self.make_heartbeat("").refresh()
        assert list(self.dir.iterdir()) == []


if __name__ == "__main__":
    unittest.main()
