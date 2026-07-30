"""
Unit tests for imapmanager.notifiers.Notifiers.
"""

import unittest
from unittest import mock

from imapmanager.constants import NOTIFIERS, REDACTED
from imapmanager.notifiers import Notifiers

TELEGRAM_CONF = {"token": "tok123", "chat_id": "chat456"}
PUSHOVER_CONF = {"token": "app123", "user_key": "usr456"}

TELEGRAM_URL = "https://api.telegram.org/bottok123/sendMessage"
PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


def make_notifiers(**sections):
    """
    Build a Notifiers with a mocked logger and only the given notifier sections.
    """
    return Notifiers(mock.MagicMock(), dict(sections))


class TestNotifiers(unittest.TestCase):
    def test_every_notifier_has_a_request_builder(self) -> None:
        # Guard against adding a notifier to NOTIFIERS without its builder.
        assert set(make_notifiers()._builders) == set(NOTIFIERS)

    def test_no_notifier_section_no_call(self) -> None:
        notifiers = make_notifiers()
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            notifiers.send("hello")
        post.assert_not_called()

    def test_unconfigured_notifier_is_skipped(self) -> None:
        # Only telegram is configured: asking for both must only send one.
        notifiers = make_notifiers(telegram=TELEGRAM_CONF)
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            post.return_value.status_code = 200
            notifiers.send("hello", ("telegram", "pushover"))
        post.assert_called_once()
        assert post.call_args.args[0] == TELEGRAM_URL

    def test_empty_notifier_section_is_skipped(self) -> None:
        # An explicitly empty section means the notifier is disabled.
        notifiers = make_notifiers(telegram=None)
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            notifiers.send("hello", ("telegram",))
        post.assert_not_called()

    def test_telegram_success_posts_form_fields_with_timeout(self) -> None:
        notifiers = make_notifiers(telegram=TELEGRAM_CONF)
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            post.return_value.status_code = 200
            notifiers.send("hello world", ("telegram",))
        post.assert_called_once_with(
            TELEGRAM_URL,
            data={"chat_id": "chat456", "text": "hello world"},
            timeout=5,
        )
        notifiers.logger.warning.assert_not_called()

    def test_pushover_success_posts_form_fields_with_timeout(self) -> None:
        notifiers = make_notifiers(pushover=PUSHOVER_CONF)
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            post.return_value.status_code = 200
            notifiers.send("hello world", ("pushover",))
        post.assert_called_once_with(
            PUSHOVER_URL,
            data={"token": "app123", "user": "usr456", "message": "hello world"},
            timeout=5,
        )
        notifiers.logger.warning.assert_not_called()

    def test_all_notifiers_used_when_names_is_none(self) -> None:
        notifiers = make_notifiers(telegram=TELEGRAM_CONF, pushover=PUSHOVER_CONF)
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            post.return_value.status_code = 200
            notifiers.send("hello")
        urls = [call.args[0] for call in post.call_args_list]
        assert sorted(urls) == sorted([TELEGRAM_URL, PUSHOVER_URL])

    def test_notifiers_are_sent_in_registry_order(self) -> None:
        notifiers = make_notifiers(telegram=TELEGRAM_CONF, pushover=PUSHOVER_CONF)
        expected = {
            "telegram": TELEGRAM_URL,
            "pushover": PUSHOVER_URL,
        }
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            post.return_value.status_code = 200
            notifiers.send("hello")
        urls = [call.args[0] for call in post.call_args_list]
        assert urls == [expected[name] for name in NOTIFIERS]

    def test_non_200_logs_warning(self) -> None:
        notifiers = make_notifiers(pushover=PUSHOVER_CONF)
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            post.return_value.status_code = 500
            post.return_value.text = "oops"
            notifiers.send("hello", ("pushover",))
        notifiers.logger.warning.assert_called_once()
        assert "pushover" in notifiers.logger.warning.call_args.args

    def test_request_exception_swallowed(self) -> None:
        notifiers = make_notifiers(telegram=TELEGRAM_CONF)
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            post.side_effect = OSError("network down")
            notifiers.send("hello", ("telegram",))
        notifiers.logger.error.assert_called_once()
        assert "telegram" in notifiers.logger.error.call_args.args

    def test_one_failing_notifier_does_not_stop_the_others(self) -> None:
        notifiers = make_notifiers(telegram=TELEGRAM_CONF, pushover=PUSHOVER_CONF)
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            post.side_effect = [
                OSError("network down"),
                mock.MagicMock(status_code=200),
            ]
            notifiers.send("hello")
        assert post.call_count == 2
        notifiers.logger.error.assert_called_once()


class TestNotifiersDoNotLeakCredentials(unittest.TestCase):
    """
    The telegram token is part of the API URL, so a <requests> error message and
    an error body echoing that URL both carry it. Nothing logged may expose it.
    """

    # What requests raises on a DNS/TCP/TLS failure: the message holds the path.
    CONNECTION_ERROR = OSError(
        "HTTPSConnectionPool(host='api.telegram.org', port=443): Max retries "
        "exceeded with url: /bottok123/sendMessage (Caused by "
        "NameResolutionError('Failed to resolve api.telegram.org'))"
    )

    def test_exception_message_does_not_leak_the_telegram_token(self) -> None:
        notifiers = make_notifiers(telegram=TELEGRAM_CONF)
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            post.side_effect = self.CONNECTION_ERROR
            notifiers.send("hello", ("telegram",))
        logged = str(notifiers.logger.error.call_args)
        assert "tok123" not in logged
        assert REDACTED in logged

    def test_traceback_is_never_logged(self) -> None:
        # logger.exception appends the traceback, whose last line is the
        # requests message holding the token: it can never be used here.
        notifiers = make_notifiers(telegram=TELEGRAM_CONF)
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            post.side_effect = self.CONNECTION_ERROR
            notifiers.send("hello", ("telegram",))
        notifiers.logger.exception.assert_not_called()

    def test_exception_message_does_not_leak_the_pushover_credentials(self) -> None:
        notifiers = make_notifiers(pushover=PUSHOVER_CONF)
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            post.side_effect = OSError("failed to post token=app123 user=usr456")
            notifiers.send("hello", ("pushover",))
        logged = str(notifiers.logger.error.call_args)
        assert "app123" not in logged
        assert "usr456" not in logged

    def test_error_body_echoing_the_url_is_redacted(self) -> None:
        # A proxy answering 502 routinely echoes the URL it could not reach.
        notifiers = make_notifiers(telegram=TELEGRAM_CONF)
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            post.return_value.status_code = 502
            post.return_value.text = f"Bad gateway for {TELEGRAM_URL}"
            notifiers.send("hello", ("telegram",))
        logged = str(notifiers.logger.warning.call_args)
        assert "tok123" not in logged
        assert REDACTED in logged

    def test_the_failure_is_still_reported(self) -> None:
        # Redacting must not silence the error: a lost notification stays visible.
        notifiers = make_notifiers(telegram=TELEGRAM_CONF)
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            post.side_effect = self.CONNECTION_ERROR
            notifiers.send("hello", ("telegram",))
        notifiers.logger.error.assert_called_once()
        logged = str(notifiers.logger.error.call_args)
        assert "telegram" in logged
        assert "OSError" in logged

    def test_a_failing_notification_still_does_not_break_the_caller(self) -> None:
        notifiers = make_notifiers(telegram=TELEGRAM_CONF)
        with mock.patch("imapmanager.notifiers.requests.post") as post:
            post.side_effect = self.CONNECTION_ERROR
            notifiers.send("hello", ("telegram",))
        # Reaching this line is the assertion: send() swallowed the error.
        notifiers.logger.error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
