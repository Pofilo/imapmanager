"""
Unit tests for imapmanager.imap.
"""

import unittest
from email import message_from_bytes, policy
from email.message import EmailMessage
from imaplib import IMAP4
from ssl import SSLError
from threading import Event
from unittest import mock

from imapmanager.constants import NOTIFIERS
from imapmanager.imap import (
    RECONNECT_MAX_AUTH_ATTEMPTS,
    SOCKET_TIMEOUT,
    TRANSIENT_ERRORS,
    Imap,
    MailAction,
    MailActions,
)


def make_config(**overrides):
    """
    Minimal valid config as a plain dict (Imap only uses get/[]).
    """
    config = {
        "hostname": "imap.example.com",
        "port": 993,
        "username": "user@example.com",
        "password": "hunter2",
        "mailbox": "INBOX",
        "pollingInterval": 60,
        "defaultFolder": "INBOX.default",
        "logLevel": "INFO",
        "filters": {
            "subject": {
                "INBOX.spam": [
                    {"pattern": "[SPAM]", "actions": ["move", "mark_as_read"]},
                ],
            },
        },
    }
    config.update(overrides)
    return config


def make_imap(config=None, stop_event=None):
    """
    Build an Imap instance without any network access and with a mocked handler.
    """
    with mock.patch.object(Imap, "_connect_with_retry", return_value=True):
        imap = Imap(
            mock.MagicMock(),
            config if config is not None else make_config(),
            stop_event if stop_event is not None else Event(),
        )
    imap._handler = mock.MagicMock()
    imap.running = True
    return imap


def make_mail_bytes(subject, from_addr, to=None, cc=None, body="hello"):
    """
    Build a raw RFC822 mail with the stdlib email package.
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    if to:
        msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg.set_content(body)
    return msg.as_bytes()


FOLDER_LIST = (
    "OK",
    [
        b'(\\HasNoChildren) "." "INBOX.spam"',
        b'(\\HasNoChildren) "." "INBOX.default"',
    ],
)


class TestMailActions(unittest.TestCase):
    def setUp(self) -> None:
        self.actions = MailActions(mock.MagicMock())

    def test_append_skips_action_without_rule_name(self) -> None:
        self.actions.append(MailAction())
        assert self.actions.get_best_action() == MailAction()

    def test_get_best_action_empty_returns_default_mailaction(self) -> None:
        assert self.actions.get_best_action() == MailAction()

    def test_get_best_action_highest_weight_wins(self) -> None:
        low = MailAction(rule_name="low", weight=1)
        high = MailAction(rule_name="high", weight=10)
        self.actions.append(low)
        self.actions.append(high)
        assert self.actions.get_best_action() is high

    def test_equal_weight_first_appended_wins(self) -> None:
        first = MailAction(rule_name="first", weight=5)
        second = MailAction(rule_name="second", weight=5)
        self.actions.append(first)
        self.actions.append(second)
        assert self.actions.get_best_action() is first


class TestConnectWithRetry(unittest.TestCase):
    def make_imap_for_retry(self, connect_side_effect):
        stop_event = mock.MagicMock()
        stop_event.is_set.return_value = False
        stop_event.wait.return_value = False
        imap = make_imap(stop_event=stop_event)
        imap._handler = None
        mock.patch.object(imap, "_connect", side_effect=connect_side_effect).start()
        self.addCleanup(mock.patch.stopall)
        return imap, stop_event

    def wait_timeouts(self, stop_event):
        return [call.kwargs["timeout"] for call in stop_event.wait.call_args_list]

    def test_success_first_attempt_no_wait(self) -> None:
        imap, stop_event = self.make_imap_for_retry([None])
        assert imap._connect_with_retry()
        stop_event.wait.assert_not_called()

    def test_transient_errors_backoff_then_success(self) -> None:
        imap, stop_event = self.make_imap_for_retry(
            [OSError("net down"), SSLError("handshake"), None]
        )
        assert imap._connect_with_retry()
        assert self.wait_timeouts(stop_event) == [5, 10]

    def test_delay_capped_at_300(self) -> None:
        failures = [OSError("net down")] * 8 + [None]
        imap, stop_event = self.make_imap_for_retry(failures)
        assert imap._connect_with_retry()
        assert self.wait_timeouts(stop_event) == [5, 10, 20, 40, 80, 160, 300, 300]

    def test_stop_during_wait_returns_false(self) -> None:
        imap, stop_event = self.make_imap_for_retry([OSError("net down")])
        stop_event.wait.return_value = True
        assert not imap._connect_with_retry()
        imap._connect.assert_called_once()

    def test_stop_event_preset_returns_false(self) -> None:
        imap, stop_event = self.make_imap_for_retry([None])
        stop_event.is_set.return_value = True
        assert not imap._connect_with_retry()
        imap._connect.assert_not_called()

    def test_socket_timeout_retries_forever_without_panicking(self) -> None:
        # A read timeout is a network fault: it must back off indefinitely, never
        # be counted as an auth failure that gives up after a handful of tries.
        failures = [TimeoutError("timed out")] * RECONNECT_MAX_AUTH_ATTEMPTS + [None]
        imap, stop_event = self.make_imap_for_retry(failures)
        assert imap._connect_with_retry()
        assert imap._connect.call_count == RECONNECT_MAX_AUTH_ATTEMPTS + 1
        assert self.wait_timeouts(stop_event) == [5, 10, 20, 40, 80]
        stop_event.set.assert_not_called()

    def test_auth_failures_panic_after_five(self) -> None:
        imap, stop_event = self.make_imap_for_retry(IMAP4.error("bad login"))
        assert not imap._connect_with_retry()
        assert imap._connect.call_count == RECONNECT_MAX_AUTH_ATTEMPTS
        assert not imap.running
        stop_event.set.assert_called_once()


class TestConnect(unittest.TestCase):
    def test_connect_logs_in_and_selects_mailbox(self) -> None:
        imap = make_imap()
        imap._handler = None
        imap.running = False
        with (
            mock.patch("imapmanager.imap.IMAP4_SSL") as imap_ssl,
            mock.patch("imapmanager.imap.create_default_context") as ctx,
        ):
            imap._connect()
        imap_ssl.assert_called_once_with(
            "imap.example.com",
            993,
            ssl_context=ctx.return_value,
            timeout=SOCKET_TIMEOUT,
        )
        handler = imap_ssl.return_value
        handler.login.assert_called_once_with("user@example.com", "hunter2")
        handler.select.assert_called_once_with('"INBOX"')
        assert imap._handler is handler
        assert imap.running

    def test_timeout_error_is_transient(self) -> None:
        # SOCKET_TIMEOUT only ever recovers because a socket timeout raises
        # TimeoutError, which TRANSIENT_ERRORS already covers through OSError.
        # If that stops holding, every read timeout becomes an unhandled crash.
        assert issubclass(TimeoutError, TRANSIENT_ERRORS)


class TestMaybeReconnect(unittest.TestCase):
    def test_none_handler_triggers_reconnect(self) -> None:
        imap = make_imap()
        imap._handler = None
        with mock.patch.object(imap, "_connect_with_retry", return_value=True) as retry:
            assert imap._maybe_reconnect()
        retry.assert_called_once()

    def test_healthy_check_returns_true(self) -> None:
        imap = make_imap()
        imap._handler.check.return_value = ("OK", [b""])
        assert imap._maybe_reconnect()

    def test_check_exception_reconnects(self) -> None:
        imap = make_imap()
        imap._handler.check.side_effect = IMAP4.abort("connection lost")
        with mock.patch.object(imap, "_connect_with_retry", return_value=True) as retry:
            assert imap._maybe_reconnect()
        assert imap._handler is None
        retry.assert_called_once()

    def test_socket_timeout_on_check_reconnects(self) -> None:
        # The keepalive check is where a half-open connection surfaces first: with
        # SOCKET_TIMEOUT it raises instead of blocking, so recovery can happen.
        imap = make_imap()
        imap._handler.check.side_effect = TimeoutError("timed out")
        with mock.patch.object(imap, "_connect_with_retry", return_value=True) as retry:
            assert imap._maybe_reconnect()
        assert imap._handler is None
        retry.assert_called_once()

    def test_falsy_check_returns_false(self) -> None:
        imap = make_imap()
        imap._handler.check.return_value = None
        assert not imap._maybe_reconnect()


class TestCheckFolderExistOnServer(unittest.TestCase):
    def test_found_with_quotes(self) -> None:
        imap = make_imap()
        imap._handler.list.return_value = FOLDER_LIST
        assert imap._check_folder_exist_on_server("INBOX.spam")

    def test_found_without_quotes(self) -> None:
        imap = make_imap()
        imap._handler.list.return_value = (
            "OK",
            [b'(\\HasNoChildren) "." INBOX.spam'],
        )
        assert imap._check_folder_exist_on_server("INBOX.spam")

    def test_not_found(self) -> None:
        imap = make_imap()
        imap._handler.list.return_value = FOLDER_LIST
        assert not imap._check_folder_exist_on_server("INBOX.other")


class TestAnalyseFiltersForCategory(unittest.TestCase):
    def setUp(self) -> None:
        self.imap = make_imap(
            make_config(
                filters={
                    "subject": {
                        "INBOX.spam": [
                            {"pattern": "[SPAM]", "actions": ["move"]},
                            {
                                "pattern": "notify me",
                                "actions": ["telegram", "mark_as_read"],
                            },
                            {
                                "pattern": "push me",
                                "actions": ["pushover", "telegram"],
                            },
                        ],
                        "INBOX.important": [
                            {
                                "pattern": "urgent",
                                "actions": ["move"],
                                "weight": 10,
                            },
                        ],
                    },
                },
            )
        )

    def test_no_rules_for_category_returns_default(self) -> None:
        action = self.imap._analyse_filters_for_category("body", "body", ["whatever"])
        assert action == MailAction()

    def test_case_insensitive_substring_match(self) -> None:
        action = self.imap._analyse_filters_for_category(
            "subject", "subject", ["Re: [spam] buy stuff"]
        )
        assert action.rule_name == "subject"
        assert action.folder == "INBOX.spam"

    def test_no_match_returns_default(self) -> None:
        action = self.imap._analyse_filters_for_category(
            "subject", "subject", ["hello there"]
        )
        assert action == MailAction()

    def test_actions_without_move_leave_folder_none(self) -> None:
        action = self.imap._analyse_filters_for_category(
            "subject", "subject", ["please notify me"]
        )
        assert action.folder is None
        assert action.notifiers == ("telegram",)
        assert action.mark_as_read

    def test_notifiers_follow_the_registry_order(self) -> None:
        # The tuple order comes from NOTIFIERS, not from the 'actions' list
        # (where the filter lists pushover first).
        action = self.imap._analyse_filters_for_category(
            "subject", "subject", ["please push me"]
        )
        assert action.notifiers == tuple(NOTIFIERS)
        assert not action.mark_as_read

    def test_entry_weight_overrides_global_weight(self) -> None:
        self.imap.config["weight"] = 3
        action = self.imap._analyse_filters_for_category(
            "subject", "subject", ["urgent matter"]
        )
        assert action.weight == 10

    def test_global_weight_used_when_entry_has_none(self) -> None:
        self.imap.config["weight"] = 3
        action = self.imap._analyse_filters_for_category(
            "subject", "subject", ["[SPAM] offer"]
        )
        assert action.weight == 3

    def test_highest_weight_wins_across_folders(self) -> None:
        action = self.imap._analyse_filters_for_category(
            "subject", "subject", ["[SPAM] urgent offer"]
        )
        assert action.folder == "INBOX.important"
        assert action.weight == 10


class TestUnsafeGetMailAction(unittest.TestCase):
    def make_msg(self, **kwargs):
        return message_from_bytes(make_mail_bytes(**kwargs), policy=policy.default)

    def test_subject_rule_matches(self) -> None:
        imap = make_imap()
        msg = self.make_msg(subject="[SPAM] hello", from_addr="a@b.com")
        action = imap._unsafe_get_mail_action(msg, "[SPAM] hello", "body")
        assert action.folder == "INBOX.spam"
        assert action.mark_as_read

    def test_from_rule_matches_and_mail_from_extracted(self) -> None:
        imap = make_imap(
            make_config(
                filters={
                    "from": {
                        "INBOX.family": [
                            {"pattern": "mom@example.com", "actions": ["move"]},
                        ],
                    },
                },
            )
        )
        msg = self.make_msg(subject="dinner", from_addr='"MOM" <Mom@Example.com>')
        action = imap._unsafe_get_mail_action(msg, "dinner", "body")
        assert action.folder == "INBOX.family"
        assert action.mail_from == "mom@example.com"

    def test_to_and_cc_populate_mail_dest(self) -> None:
        imap = make_imap()
        msg = self.make_msg(
            subject="hi",
            from_addr="a@b.com",
            to="First.Dest@example.com",
            cc="second.dest@example.com",
        )
        action = imap._unsafe_get_mail_action(msg, "hi", "body")
        assert action.mail_dest == ["first.dest@example.com", "second.dest@example.com"]

    def test_no_match_falls_back_to_default_folder(self) -> None:
        imap = make_imap()
        msg = self.make_msg(subject="regular mail", from_addr="a@b.com")
        action = imap._unsafe_get_mail_action(msg, "regular mail", "body")
        assert action.folder == "INBOX.default"
        assert action.rule_name is None


class ProcessMailsTestCase(unittest.TestCase):
    """
    Shared machinery: a mocked handler whose uid() dispatches per command.
    """

    def setUp(self) -> None:
        self.imap = make_imap()
        self.stop_event = Event()
        self.handler = self.imap._handler
        self.handler.list.return_value = FOLDER_LIST
        self.uid_responses = {
            "SEARCH": ("OK", [b"1"]),
            "FETCH": (
                "OK",
                [
                    (
                        b"1 (BODY[] {42}",
                        make_mail_bytes(
                            subject="[SPAM] buy stuff", from_addr="spammer@evil.com"
                        ),
                    ),
                ],
            ),
            "STORE": ("OK", [b""]),
            "COPY": ("OK", [b""]),
            "EXPUNGE": ("OK", [b""]),
        }
        self.handler.uid.side_effect = self.dispatch_uid
        patcher = mock.patch.object(self.imap, "_maybe_reconnect", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def dispatch_uid(self, command, *_args):
        response = self.uid_responses[command]
        if isinstance(response, Exception):
            raise response
        return response

    def uid_calls(self, command):
        return [
            call for call in self.handler.uid.call_args_list if call.args[0] == command
        ]


class TestProcessMails(ProcessMailsTestCase):
    def test_reconnect_failure_returns_early(self) -> None:
        self.imap._maybe_reconnect.return_value = False
        self.imap.process_mails(self.stop_event)
        self.handler.select.assert_not_called()

    def test_select_failure_clears_handler(self) -> None:
        self.handler.select.side_effect = IMAP4.abort("gone")
        self.imap.process_mails(self.stop_event)
        assert self.imap._handler is None
        self.handler.uid.assert_not_called()

    def test_no_unseen_mails_no_fetch(self) -> None:
        self.uid_responses["SEARCH"] = ("OK", [b""])
        self.imap.process_mails(self.stop_event)
        assert self.uid_calls("FETCH") == []

    def test_search_failure_panics(self) -> None:
        self.uid_responses["SEARCH"] = ("NO", [b"err"])
        self.imap.process_mails(self.stop_event)
        assert not self.imap.running
        assert self.imap._stop_event.is_set()

    def test_happy_path_moves_and_expunges(self) -> None:
        self.imap.process_mails(self.stop_event)
        commands = [call.args for call in self.handler.uid.call_args_list]
        assert commands == [
            ("SEARCH", None, "UNSEEN"),
            ("FETCH", "1", "(BODY.PEEK[])"),
            ("STORE", "1", "+FLAGS", "\\Seen"),
            ("COPY", "1", '"INBOX.spam"'),
            ("STORE", "1", "+FLAGS", "\\Deleted"),
            ("EXPUNGE", "1"),
        ]

    def test_multiple_uids_all_processed(self) -> None:
        self.uid_responses["SEARCH"] = ("OK", [b"1 2 3"])
        self.imap.process_mails(self.stop_event)
        assert [call.args[1] for call in self.uid_calls("FETCH")] == ["1", "2", "3"]
        assert len(self.uid_calls("EXPUNGE")) == 3

    def test_vanished_mail_skipped(self) -> None:
        self.uid_responses["FETCH"] = ("OK", [None])
        self.imap.process_mails(self.stop_event)
        assert self.uid_calls("COPY") == []
        assert self.imap.running

    def test_fetch_failure_panics(self) -> None:
        self.uid_responses["FETCH"] = ("NO", [b"err"])
        self.imap.process_mails(self.stop_event)
        assert not self.imap.running
        assert self.uid_calls("COPY") == []

    def test_missing_folder_falls_back_to_default_not_marked_read(self) -> None:
        # Server only knows the default folder: the spam target is missing.
        self.handler.list.return_value = (
            "OK",
            [b'(\\HasNoChildren) "." "INBOX.default"'],
        )
        self.imap.process_mails(self.stop_event)
        copy_calls = self.uid_calls("COPY")
        assert copy_calls[0].args[2] == '"INBOX.default"'
        # No mark-as-read STORE, only the delete STORE.
        store_flags = [call.args[3] for call in self.uid_calls("STORE")]
        assert store_flags == ["\\Deleted"]

    def test_missing_default_folder_panics(self) -> None:
        self.handler.list.return_value = ("OK", [b'(\\HasNoChildren) "." "INBOX"'])
        self.imap.process_mails(self.stop_event)
        assert not self.imap.running
        assert self.uid_calls("COPY") == []

    def test_telegram_notification_sent_when_action(self) -> None:
        self.imap.config["filters"]["subject"]["INBOX.spam"][0]["actions"] = [
            "move",
            "telegram",
        ]
        with mock.patch.object(self.imap.notifiers, "send") as notify:
            self.imap.process_mails(self.stop_event)
        notify.assert_called_once()
        assert "[SPAM] buy stuff" in notify.call_args.args[0]
        assert notify.call_args.args[1] == ("telegram",)

    def test_pushover_notification_sent_when_action(self) -> None:
        self.imap.config["filters"]["subject"]["INBOX.spam"][0]["actions"] = [
            "move",
            "pushover",
        ]
        with mock.patch.object(self.imap.notifiers, "send") as notify:
            self.imap.process_mails(self.stop_event)
        notify.assert_called_once()
        assert "[SPAM] buy stuff" in notify.call_args.args[0]
        assert notify.call_args.args[1] == ("pushover",)

    def test_both_notifications_sent_when_both_actions(self) -> None:
        self.imap.config["filters"]["subject"]["INBOX.spam"][0]["actions"] = [
            "move",
            "pushover",
            "telegram",
        ]
        with mock.patch.object(self.imap.notifiers, "send") as notify:
            self.imap.process_mails(self.stop_event)
        notify.assert_called_once()
        assert notify.call_args.args[1] == tuple(NOTIFIERS)

    def test_no_notification_sent_without_notifier_action(self) -> None:
        with mock.patch.object(self.imap.notifiers, "send") as notify:
            self.imap.process_mails(self.stop_event)
        notify.assert_not_called()

    def test_stop_event_set_aborts_before_processing(self) -> None:
        self.stop_event.set()
        self.imap.process_mails(self.stop_event)
        assert self.uid_calls("FETCH") == []

    def test_search_exception_clears_handler(self) -> None:
        self.uid_responses["SEARCH"] = OSError("connection reset")
        self.imap.process_mails(self.stop_event)
        assert self.imap._handler is None
        assert self.uid_calls("FETCH") == []

    def test_mark_read_failure_panics(self) -> None:
        self.uid_responses["STORE"] = ("NO", [b"err"])
        self.imap.process_mails(self.stop_event)
        assert not self.imap.running
        assert self.uid_calls("COPY") == []

    def test_copy_failure_panics(self) -> None:
        self.uid_responses["COPY"] = ("NO", [b"err"])
        self.imap.process_mails(self.stop_event)
        assert not self.imap.running
        assert self.uid_calls("EXPUNGE") == []

    def test_delete_failure_panics(self) -> None:
        def dispatch(command, *args):
            if command == "STORE" and args[2] == "\\Deleted":
                return ("NO", [b"err"])
            return self.dispatch_uid(command, *args)

        self.handler.uid.side_effect = dispatch
        self.imap.process_mails(self.stop_event)
        assert not self.imap.running
        assert len(self.uid_calls("COPY")) == 1
        assert self.uid_calls("EXPUNGE") == []

    def test_expunge_failure_panics(self) -> None:
        self.uid_responses["EXPUNGE"] = ("NO", [b"err"])
        self.imap.process_mails(self.stop_event)
        assert not self.imap.running

    def test_transient_error_during_actions_clears_handler(self) -> None:
        self.uid_responses["COPY"] = OSError("connection reset")
        self.imap.process_mails(self.stop_event)
        assert self.imap._handler is None
        assert self.imap.running

    def test_body_with_unknown_charset_decoded_via_fallback(self) -> None:
        # get_content() raises LookupError on the bogus charset; the raw
        # payload is then decoded with the utf-8 fallback and the body
        # filter must still match.
        self.imap.config["filters"]["body"] = {
            "INBOX.bodyrule": [{"pattern": "bonjour", "actions": ["move"]}],
        }
        self.handler.list.return_value = (
            "OK",
            [b'(\\HasNoChildren) "." "INBOX.bodyrule"'],
        )
        raw = (
            b"Subject: hi\r\n"
            b"From: a@b.com\r\n"
            b"Content-Type: text/plain; charset=x-bogus\r\n"
            b"\r\n"
            b"bonjour tout le monde\r\n"
        )
        self.uid_responses["FETCH"] = ("OK", [(b"1 (BODY[] {21}", raw)])
        self.imap.process_mails(self.stop_event)
        assert self.uid_calls("COPY")[0].args[2] == '"INBOX.bodyrule"'

    def test_undecodable_body_gives_up_and_uses_default_folder(self) -> None:
        # Both charset decodes fail: the body is dropped and the mail still
        # gets processed (moved to the default folder).
        mail_msg = mock.MagicMock()
        mail_msg.__getitem__.return_value = None  # Subject/From/To/Cc headers
        body = mail_msg.get_body.return_value
        body.get_content.side_effect = LookupError("bad charset")
        body.get_content_charset.return_value = "x-bogus"
        body.get_payload.return_value.decode.side_effect = LookupError("still bad")
        with mock.patch(
            "imapmanager.imap.email.message_from_bytes", return_value=mail_msg
        ):
            self.imap.process_mails(self.stop_event)
        assert self.uid_calls("COPY")[0].args[2] == '"INBOX.default"'

    def test_body_without_payload_dropped_and_uses_default_folder(self) -> None:
        mail_msg = mock.MagicMock()
        mail_msg.__getitem__.return_value = None
        body = mail_msg.get_body.return_value
        body.get_content.side_effect = LookupError("bad charset")
        body.get_payload.return_value = None
        with mock.patch(
            "imapmanager.imap.email.message_from_bytes", return_value=mail_msg
        ):
            self.imap.process_mails(self.stop_event)
        assert self.uid_calls("COPY")[0].args[2] == '"INBOX.default"'

    def test_transient_error_during_fetch_clears_handler_and_returns(self) -> None:
        self.uid_responses["FETCH"] = OSError("connection reset")
        self.imap.process_mails(self.stop_event)
        assert self.imap._handler is None
        assert self.uid_calls("COPY") == []

    def test_unexpected_error_moves_mail_to_default_folder(self) -> None:
        self.uid_responses["FETCH"] = ValueError("boom")
        self.imap.process_mails(self.stop_event)
        copy_calls = self.uid_calls("COPY")
        assert copy_calls[0].args[2] == '"INBOX.default"'


class TestPanicAndLogout(unittest.TestCase):
    def test_panic_stops_running_logs_out_sets_event(self) -> None:
        stop_event = Event()
        imap = make_imap(stop_event=stop_event)
        handler = imap._handler
        handler.state = "SELECTED"
        imap.panic("something broke")
        assert not imap.running
        imap.logger.critical.assert_called_once_with("something broke")
        handler.logout.assert_called_once()
        assert stop_event.is_set()

    def test_panic_notifies_every_notifier(self) -> None:
        imap = make_imap()
        with mock.patch.object(imap.notifiers, "send") as send:
            imap.panic("something broke")
        # No explicit notifier names means "every configured one".
        send.assert_called_once_with("something broke")

    def test_logout_without_handler_is_noop(self) -> None:
        imap = make_imap()
        imap._handler = None
        imap.logout()  # must not raise

    def test_logout_selected_state_closes_then_logs_out(self) -> None:
        imap = make_imap()
        handler = imap._handler
        handler.state = "SELECTED"
        imap.logout()
        handler.close.assert_called_once()
        handler.logout.assert_called_once()
        assert imap._handler is None

    def test_logout_non_selected_state_skips_close(self) -> None:
        imap = make_imap()
        handler = imap._handler
        handler.state = "AUTH"
        imap.logout()
        handler.close.assert_not_called()
        handler.logout.assert_called_once()

    def test_logout_close_failure_still_logs_out(self) -> None:
        imap = make_imap()
        handler = imap._handler
        handler.state = "SELECTED"
        handler.close.side_effect = IMAP4.abort("gone")
        imap.logout()
        handler.logout.assert_called_once()
        assert imap._handler is None

    def test_logout_failure_logged_and_handler_cleared(self) -> None:
        imap = make_imap()
        handler = imap._handler
        handler.state = "AUTH"
        handler.logout.side_effect = OSError("gone")
        imap.logout()
        imap.logger.error.assert_called_once()
        assert imap._handler is None


if __name__ == "__main__":
    unittest.main()
