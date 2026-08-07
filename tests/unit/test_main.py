"""
Unit tests for imapmanager.__init__ (main entry point).
"""

import unittest
from signal import SIGINT, SIGTERM
from unittest import mock

import imapmanager
from imapmanager.constants import EXIT_FATAL, EXIT_OK, HEARTBEAT_GRACE


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
            mock.patch("imapmanager.Heartbeat"),
            mock.patch("imapmanager.signal") as signal_mock,
        ):
            imap = imap_cls.return_value
            # Stop the loop after the first iteration.
            imap.running = False
            imap.fatal = False
            assert imapmanager.main() == EXIT_OK

        conf_cls.assert_called_once()
        assert signal_mock.call_count == 2
        imap.process_mails.assert_called_once_with(imapmanager.stop_event)
        imap.logout.assert_called_once()
        assert imapmanager.stop_event.is_set()

    def test_heartbeat_published_before_connecting_and_each_iteration(self) -> None:
        # Imap() connects, which can block; the first heartbeat must already be
        # on disk by then or the container looks unhealthy while starting up.
        config = {"logLevel": "INFO", "pollingInterval": 1}
        calls = []
        with (
            mock.patch("imapmanager.ImapConf", return_value=config),
            mock.patch("imapmanager.Imap") as imap_cls,
            mock.patch("imapmanager.Heartbeat") as heartbeat_cls,
            mock.patch("imapmanager.signal"),
        ):
            imap = imap_cls.return_value
            imap.running = False
            imap.fatal = False
            heartbeat = heartbeat_cls.return_value
            heartbeat.refresh.side_effect = lambda *_: calls.append("refresh")
            imap_cls.side_effect = lambda *_: calls.append("Imap") or imap
            imapmanager.main()

        assert calls == ["refresh", "Imap", "refresh"]
        # The daemon and the healthcheck must share one heartbeat instance.
        assert imap_cls.call_args.args[3] is heartbeat
        assert heartbeat_cls.call_args.kwargs["valid_for"] == 1 + HEARTBEAT_GRACE

    def test_process_mails_exception_does_not_crash_loop(self) -> None:
        config = {"logLevel": "INFO", "pollingInterval": 1}
        with (
            mock.patch("imapmanager.ImapConf", return_value=config),
            mock.patch("imapmanager.Imap") as imap_cls,
            mock.patch("imapmanager.Heartbeat"),
            mock.patch("imapmanager.signal"),
        ):
            imap = imap_cls.return_value
            imap.running = False
            imap.fatal = False
            imap.process_mails.side_effect = ValueError("boom")
            assert imapmanager.main() == EXIT_OK  # must not raise

        imap.logout.assert_called_once()

    def test_fatal_error_exits_non_zero(self) -> None:
        # `restart: unless-stopped` restarts on *any* exit, code 0 included, so a
        # clean exit after a panic loops forever. Only a non-zero code lets a
        # `restart: on-failure` policy give up.
        config = {"logLevel": "INFO", "pollingInterval": 1}
        with (
            mock.patch("imapmanager.ImapConf", return_value=config),
            mock.patch("imapmanager.Imap") as imap_cls,
            mock.patch("imapmanager.Heartbeat"),
            mock.patch("imapmanager.signal"),
        ):
            imap = imap_cls.return_value
            # panic() sets both and the stop event, before main() enters the loop.
            imap.running = False
            imap.fatal = True
            imapmanager.stop_event.set()
            assert imapmanager.main() == EXIT_FATAL

        imap.process_mails.assert_not_called()
        imap.logout.assert_called_once()

    def test_signal_during_startup_exits_zero(self) -> None:
        # A SIGTERM caught while Imap() is still backing off leaves running=False
        # without a panic: that is a clean shutdown, not a failure to restart on.
        config = {"logLevel": "INFO", "pollingInterval": 1}
        with (
            mock.patch("imapmanager.ImapConf", return_value=config),
            mock.patch("imapmanager.Imap") as imap_cls,
            mock.patch("imapmanager.Heartbeat"),
            mock.patch("imapmanager.signal"),
        ):
            imap = imap_cls.return_value
            imap.running = False
            imap.fatal = False
            imap_cls.side_effect = lambda *_: imapmanager.stop_event.set() or imap
            assert imapmanager.main() == EXIT_OK

        imap.process_mails.assert_not_called()
        imap.logout.assert_called_once()


if __name__ == "__main__":
    unittest.main()
