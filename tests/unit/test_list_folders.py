"""
Unit tests for imapmanager.scripts.list_folders.
"""

import unittest
from unittest import mock

import pytest

from imapmanager.scripts.list_folders import list_folders, main, parse_args


class TestParseArgs(unittest.TestCase):
    def test_positionals_parsed(self) -> None:
        argv = ["list-folders", "imap.example.com", "user@example.com", "hunter2"]
        with mock.patch("sys.argv", argv):
            args = parse_args()
        assert args.hostname == "imap.example.com"
        assert args.username == "user@example.com"
        assert args.password == "hunter2"

    def test_default_port_993(self) -> None:
        argv = ["list-folders", "host", "user", "pass"]
        with mock.patch("sys.argv", argv):
            assert parse_args().port == 993

    def test_custom_port_flag(self) -> None:
        argv = ["list-folders", "host", "user", "pass", "--port", "1993"]
        with mock.patch("sys.argv", argv):
            assert parse_args().port == 1993

    def test_missing_positional_exits(self) -> None:
        with (
            mock.patch("sys.argv", ["list-folders", "host"]),
            mock.patch("sys.stderr"),
            pytest.raises(SystemExit),
        ):
            parse_args()


class TestListFolders(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = mock.MagicMock()
        patcher = mock.patch("imapmanager.scripts.list_folders.IMAP4_SSL")
        self.imap_cls = patcher.start()
        self.addCleanup(patcher.stop)
        self.mail = self.imap_cls.return_value.__enter__.return_value

    def call(self) -> None:
        list_folders("host", 993, "user", "pass", self.logger)

    def test_logs_each_folder_on_ok(self) -> None:
        self.mail.list.return_value = ("OK", [b"INBOX", b"INBOX.spam"])
        self.call()
        self.mail.login.assert_called_once_with("user", "pass")
        logged = [call.args[0] for call in self.logger.info.call_args_list]
        assert "INBOX" in logged
        assert "INBOX.spam" in logged

    def test_error_status_logs_error(self) -> None:
        self.mail.list.return_value = ("NO", [b"err"])
        self.call()
        self.logger.error.assert_called_once_with("Failed to list folders.")

    def test_connection_exception_logged_not_raised(self) -> None:
        self.mail.login.side_effect = OSError("connection refused")
        self.call()  # must not raise
        self.logger.exception.assert_called_once()


class TestMain(unittest.TestCase):
    def test_main_wires_args_to_list_folders(self) -> None:
        argv = ["list-folders", "host", "user", "pass", "--port", "1993"]
        with (
            mock.patch("sys.argv", argv),
            mock.patch("imapmanager.scripts.list_folders.list_folders") as list_mock,
        ):
            main()
        args = list_mock.call_args.args
        assert args[:4] == ("host", 1993, "user", "pass")


if __name__ == "__main__":
    unittest.main()
