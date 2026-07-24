"""
Unit tests for imapmanager.__init__ (main entry point).
"""

import unittest
from signal import SIGINT, SIGTERM
from unittest import mock

import imapmanager


class TestSignalHandler(unittest.TestCase):
    def setUp(self) -> None:
        imapmanager.stop_event.clear()
        self.addCleanup(imapmanager.stop_event.clear)

    def test_sigterm_sets_stop_event(self) -> None:
        assert not imapmanager.stop_event.is_set()
        imapmanager.signal_handler(SIGTERM, None)
        assert imapmanager.stop_event.is_set()

    def test_sigint_sets_stop_event(self) -> None:
        assert not imapmanager.stop_event.is_set()
        imapmanager.signal_handler(SIGINT, None)
        assert imapmanager.stop_event.is_set()

    def test_multiple_calls_stay_set(self) -> None:
        imapmanager.signal_handler(SIGINT, None)
        imapmanager.signal_handler(SIGTERM, None)
        assert imapmanager.stop_event.is_set()


class TestMain(unittest.TestCase):
    def setUp(self) -> None:
        imapmanager.stop_event.clear()
        self.addCleanup(imapmanager.stop_event.clear)

    def test_single_iteration_then_logout(self) -> None:
        config = {"logLevel": "INFO", "pollingInterval": 1}
        with (
            mock.patch("imapmanager.ImapConf", return_value=config) as conf_cls,
            mock.patch("imapmanager.Imap") as imap_cls,
            mock.patch("imapmanager.signal") as signal_mock,
        ):
            imap = imap_cls.return_value
            # Stop the loop after the first iteration.
            imap.running = False
            imapmanager.main()

        conf_cls.assert_called_once()
        assert signal_mock.call_count == 2
        imap.process_mails.assert_called_once_with(imapmanager.stop_event)
        imap.logout.assert_called_once()
        assert imapmanager.stop_event.is_set()

    def test_process_mails_exception_does_not_crash_loop(self) -> None:
        config = {"logLevel": "INFO", "pollingInterval": 1}
        with (
            mock.patch("imapmanager.ImapConf", return_value=config),
            mock.patch("imapmanager.Imap") as imap_cls,
            mock.patch("imapmanager.signal"),
        ):
            imap = imap_cls.return_value
            imap.running = False
            imap.process_mails.side_effect = ValueError("boom")
            imapmanager.main()  # must not raise

        imap.logout.assert_called_once()


if __name__ == "__main__":
    unittest.main()
