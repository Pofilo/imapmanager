"""
Unit tests for imapmanager.conf.ImapConf.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pytest

from imapmanager.conf import ImapConf
from imapmanager.constants import CONFIG_PATH_NAME

VALID_CONFIG = """\
hostname: imap.example.com
port: 993
username: user@example.com
password: hunter2
mailbox: INBOX
pollingInterval: 60
defaultFolder: INBOX.default
logLevel: INFO
filters:
  subject:
    INBOX.spam:
      - pattern: '[SPAM]'
        actions: [move, mark_as_read, telegram]
"""

MANDATORY_KEYS = (
    "hostname",
    "port",
    "username",
    "password",
    "mailbox",
    "pollingInterval",
    "defaultFolder",
    "logLevel",
    "filters",
)


class ImapConfTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = mock.MagicMock()
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)

    def write_config(self, text):
        path = Path(self._tmp_dir.name) / "imapmanager.conf.yml"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def make_conf(self, text):
        with mock.patch.dict("os.environ", {CONFIG_PATH_NAME: self.write_config(text)}):
            return ImapConf(logger=self.logger)

    def assert_exits(self, text) -> None:
        with pytest.raises(SystemExit) as ctx:
            self.make_conf(text)
        assert ctx.value.code == 1


class TestImapConfLoading(ImapConfTestCase):
    def test_valid_config_loads_as_dict(self) -> None:
        conf = self.make_conf(VALID_CONFIG)
        assert conf["hostname"] == "imap.example.com"
        assert conf.get("port") == 993
        assert "INBOX.spam" in conf["filters"]["subject"]

    def test_missing_file_exits(self) -> None:
        missing = str(Path(self._tmp_dir.name) / "nope.yml")
        with (
            mock.patch.dict("os.environ", {CONFIG_PATH_NAME: missing}),
            pytest.raises(SystemExit) as ctx,
        ):
            ImapConf(logger=self.logger)
        assert ctx.value.code == 1
        self.logger.critical.assert_called_once()
        assert missing in self.logger.critical.call_args.args

    def test_default_path_when_env_unset(self) -> None:
        # Without the env var, the default /etc/imapmanager.conf.yml is used;
        # pretend it does not exist.
        with mock.patch.dict("os.environ"):
            os.environ.pop(CONFIG_PATH_NAME, None)
            with mock.patch("imapmanager.conf.Path") as mock_path:
                mock_path.return_value.is_file.return_value = False
                with pytest.raises(SystemExit):
                    ImapConf(logger=self.logger)
        mock_path.assert_any_call("/etc/imapmanager.conf.yml")
        self.logger.critical.assert_called_once()

    def test_invalid_yaml_exits(self) -> None:
        self.assert_exits("::: [ not yaml\n  - {")
        self.logger.critical.assert_called_once()
        assert "Parsing while reading conf" in self.logger.critical.call_args.args[0]

    def test_empty_yaml_exits(self) -> None:
        self.assert_exits("")
        assert "must contain a YAML mapping" in self.logger.critical.call_args.args[0]
        assert "NoneType" in self.logger.critical.call_args.args

    def test_list_yaml_exits(self) -> None:
        self.assert_exits("- hostname: imap.example.com\n- port: 993\n")
        assert "must contain a YAML mapping" in self.logger.critical.call_args.args[0]
        assert "list" in self.logger.critical.call_args.args

    def test_unreadable_file_exits(self) -> None:
        with mock.patch("imapmanager.conf.Path") as mock_path:
            mock_path.return_value.is_file.return_value = True
            mock_path.return_value.open.side_effect = OSError("permission denied")
            with pytest.raises(SystemExit) as ctx:
                ImapConf(logger=self.logger)
        assert ctx.value.code == 1
        assert "Reading conf" in self.logger.critical.call_args.args[0]


class TestImapConfValidation(ImapConfTestCase):
    def test_each_missing_mandatory_key_exits(self) -> None:
        for key in MANDATORY_KEYS:
            with self.subTest(key=key):
                self.logger.reset_mock()
                lines = VALID_CONFIG.splitlines(keepends=True)
                if key == "filters":
                    text = "".join(lines[:9])  # drop the whole filters block
                else:
                    text = "".join(
                        line for line in lines if not line.startswith(f"{key}:")
                    )
                self.assert_exits(text)
                self.logger.critical.assert_called_once()

    def test_port_out_of_range_exits(self) -> None:
        for bad_port in ("0", "-1", "65536"):
            with self.subTest(port=bad_port):
                self.logger.reset_mock()
                self.assert_exits(
                    VALID_CONFIG.replace("port: 993", f"port: {bad_port}")
                )
                assert "port" in self.logger.critical.call_args.args
                assert "must be" in self.logger.critical.call_args.args[0]

    def test_port_wrong_type_exits(self) -> None:
        # A quoted number and a boolean are both invalid ports.
        for bad_port in ("'993'", "true"):
            with self.subTest(port=bad_port):
                self.logger.reset_mock()
                self.assert_exits(
                    VALID_CONFIG.replace("port: 993", f"port: {bad_port}")
                )
                assert "port" in self.logger.critical.call_args.args
                assert "must be of type" in self.logger.critical.call_args.args[0]

    def test_polling_interval_wrong_type_exits(self) -> None:
        self.assert_exits(
            VALID_CONFIG.replace("pollingInterval: 60", "pollingInterval: 10s")
        )
        assert "pollingInterval" in self.logger.critical.call_args.args
        assert "must be of type" in self.logger.critical.call_args.args[0]

    def test_polling_interval_below_minimum_exits(self) -> None:
        self.assert_exits(
            VALID_CONFIG.replace("pollingInterval: 60", "pollingInterval: 0")
        )
        assert "pollingInterval" in self.logger.critical.call_args.args

    def test_polling_interval_float_accepted(self) -> None:
        conf = self.make_conf(
            VALID_CONFIG.replace("pollingInterval: 60", "pollingInterval: 2.5")
        )
        assert conf["pollingInterval"] == 2.5

    def test_hostname_wrong_type_exits(self) -> None:
        self.assert_exits(
            VALID_CONFIG.replace("hostname: imap.example.com", "hostname: 993")
        )
        assert "hostname" in self.logger.critical.call_args.args
        assert "must be of type" in self.logger.critical.call_args.args[0]

    def test_empty_string_value_exits(self) -> None:
        self.assert_exits(
            VALID_CONFIG.replace("hostname: imap.example.com", "hostname: ''")
        )
        assert "hostname" in self.logger.critical.call_args.args
        assert "is empty" in self.logger.critical.call_args.args[0]

    def test_empty_filters_exits(self) -> None:
        lines = VALID_CONFIG.splitlines(keepends=True)
        self.assert_exits("".join(lines[:9]) + "filters: {}\n")
        assert "filters" in self.logger.critical.call_args.args
        assert "is empty" in self.logger.critical.call_args.args[0]

    def test_log_level_aliases_accepted(self) -> None:
        # FATAL and WARN are documented and valid logging aliases.
        for level in ("FATAL", "WARN", "DEBUG", "CRITICAL"):
            with self.subTest(level=level):
                conf = self.make_conf(
                    VALID_CONFIG.replace("logLevel: INFO", f"logLevel: {level}")
                )
                assert conf["logLevel"] == level

    def test_lowercase_log_level_exits(self) -> None:
        self.assert_exits(VALID_CONFIG.replace("logLevel: INFO", "logLevel: info"))
        assert "logLevel" in self.logger.critical.call_args.args[0]
        assert "info" in self.logger.critical.call_args.args

    def test_typo_log_level_exits(self) -> None:
        self.assert_exits(VALID_CONFIG.replace("logLevel: INFO", "logLevel: INF"))
        assert "logLevel" in self.logger.critical.call_args.args[0]
        assert "INF" in self.logger.critical.call_args.args
        self.assert_exits(VALID_CONFIG.replace("logLevel: INFO", "logLevel: INFOO"))
        assert "logLevel" in self.logger.critical.call_args.args[0]
        assert "INFOO" in self.logger.critical.call_args.args

    def test_filter_pattern_wrong_type_exits(self) -> None:
        # Unquoted YAML scalars: date, bool, number and null are not strings.
        for bad_pattern in ("2026-07-16", "true", "42", "null", "''"):
            with self.subTest(pattern=bad_pattern):
                self.logger.reset_mock()
                self.assert_exits(
                    VALID_CONFIG.replace(
                        "- pattern: '[SPAM]'", f"- pattern: {bad_pattern}"
                    )
                )
                assert "pattern" in self.logger.critical.call_args.args
                assert (
                    "must be a non-empty string"
                    in self.logger.critical.call_args.args[0]
                )

    def test_filter_weight_accepted(self) -> None:
        conf = self.make_conf(
            VALID_CONFIG.replace(
                "- pattern: '[SPAM]'",
                "- pattern: '[SPAM]'\n        weight: 5",
            )
        )
        assert conf["filters"]["subject"]["INBOX.spam"][0]["weight"] == 5

    def test_filter_weight_wrong_type_exits(self) -> None:
        for bad_weight in ("'100'", "true", "null", "1.5"):
            with self.subTest(weight=bad_weight):
                self.logger.reset_mock()
                self.assert_exits(
                    VALID_CONFIG.replace(
                        "- pattern: '[SPAM]'",
                        f"- pattern: '[SPAM]'\n        weight: {bad_weight}",
                    )
                )
                assert "weight" in self.logger.critical.call_args.args
                assert "must be of type int" in self.logger.critical.call_args.args[0]

    def test_default_weight_accepted(self) -> None:
        conf = self.make_conf(VALID_CONFIG + "weight: 10\n")
        assert conf["weight"] == 10

    def test_default_weight_zero_accepted(self) -> None:
        conf = self.make_conf(VALID_CONFIG + "weight: 0\n")
        assert conf["weight"] == 0

    def test_default_weight_wrong_type_exits(self) -> None:
        self.assert_exits(VALID_CONFIG + "weight: '10'\n")
        assert "weight" in self.logger.critical.call_args.args
        assert "must be of type" in self.logger.critical.call_args.args[0]

    def test_unknown_filter_category_exits(self) -> None:
        self.assert_exits(VALID_CONFIG.replace("  subject:", "  bogus:"))
        assert "bogus" in self.logger.critical.call_args.args

    def test_filter_entry_missing_pattern_exits(self) -> None:
        self.assert_exits(VALID_CONFIG.replace("- pattern: '[SPAM]'", "- weight: 3"))
        assert "pattern" in self.logger.critical.call_args.args

    def test_filter_entry_missing_actions_exits(self) -> None:
        self.assert_exits(
            VALID_CONFIG.replace("        actions: [move, mark_as_read, telegram]", "")
        )
        assert "actions" in self.logger.critical.call_args.args

    def test_filter_bad_action_mark_as_read(self) -> None:
        self.assert_exits(
            VALID_CONFIG.replace(
                "        actions: [move, mark_as_read, telegram]",
                "        actions: [mark_as_red]",
            )
        )
        assert "unknown action" in self.logger.critical.call_args.args[0]

    def test_filter_bad_action_move(self) -> None:
        self.assert_exits(
            VALID_CONFIG.replace(
                "        actions: [move, mark_as_read, telegram]",
                "        actions: [mov]",
            )
        )
        assert "unknown action" in self.logger.critical.call_args.args[0]

    def test_filter_bad_action_telegram(self) -> None:
        self.assert_exits(
            VALID_CONFIG.replace(
                "        actions: [move, mark_as_read, telegram]",
                "        actions: [signal]",
            )
        )
        assert "unknown action" in self.logger.critical.call_args.args[0]

    def test_filter_category_not_mapping_exits(self) -> None:
        self.assert_exits(
            VALID_CONFIG.replace(
                "    INBOX.spam:\n      - pattern: '[SPAM]'\n"
                "        actions: [move, mark_as_read, telegram]\n",
                "    - INBOX.spam\n",
            )
        )
        assert "must be a mapping of folders" in self.logger.critical.call_args.args[0]

    def test_filter_entries_not_list_exits(self) -> None:
        self.assert_exits(
            VALID_CONFIG.replace(
                "    INBOX.spam:\n      - pattern: '[SPAM]'\n"
                "        actions: [move, mark_as_read, telegram]\n",
                "    INBOX.spam: '[SPAM]'\n",
            )
        )
        assert "must be a list of filters" in self.logger.critical.call_args.args[0]

    def test_filter_entry_not_mapping_exits(self) -> None:
        self.assert_exits(
            VALID_CONFIG.replace(
                "      - pattern: '[SPAM]'\n"
                "        actions: [move, mark_as_read, telegram]\n",
                "      - '[SPAM]'\n",
            )
        )
        assert "must be a mapping" in self.logger.critical.call_args.args[0]


class TestImapConfTelegramValidation(ImapConfTestCase):
    TELEGRAM_SECTION = "telegram:\n  token: secret-token\n  chat_id: secret-chat\n"

    def test_valid_telegram_section_loads(self) -> None:
        conf = self.make_conf(VALID_CONFIG + self.TELEGRAM_SECTION)
        assert conf["telegram"]["token"] == "secret-token"
        assert conf["telegram"]["chat_id"] == "secret-chat"

    def test_no_telegram_section_ok(self) -> None:
        conf = self.make_conf(VALID_CONFIG)
        assert "telegram" not in conf

    def test_empty_telegram_section_ok(self) -> None:
        # An explicitly empty section means "telegram disabled".
        conf = self.make_conf(VALID_CONFIG + "telegram:\n")
        assert conf["telegram"] is None

    def test_telegram_missing_token_exits(self) -> None:
        self.assert_exits(VALID_CONFIG + "telegram:\n  chat_id: secret-chat\n")
        assert "token" in self.logger.critical.call_args.args

    def test_telegram_missing_chat_id_exits(self) -> None:
        self.assert_exits(VALID_CONFIG + "telegram:\n  token: secret-token\n")
        assert "chat_id" in self.logger.critical.call_args.args

    def test_telegram_mistyped_chat_id_exits(self) -> None:
        self.assert_exits(
            VALID_CONFIG + "telegram:\n  token: secret-token\n  chatid: oops\n"
        )
        assert "chat_id" in self.logger.critical.call_args.args

    def test_telegram_falsy_token_exits(self) -> None:
        self.assert_exits(VALID_CONFIG + "telegram:\n  token: ''\n  chat_id: c\n")
        assert "token" in self.logger.critical.call_args.args

    def test_telegram_non_dict_section_exits(self) -> None:
        self.assert_exits(VALID_CONFIG + "telegram: not-a-mapping\n")
        self.logger.critical.assert_called_once()


class TestImapConfDebugMasking(ImapConfTestCase):
    def test_debug_masks_password_and_telegram(self) -> None:
        text = VALID_CONFIG.replace("logLevel: INFO", "logLevel: DEBUG")
        text += "telegram:\n  token: secret-token\n  chat_id: secret-chat\n"
        conf = self.make_conf(text)

        self.logger.debug.assert_called_once()
        dumped = self.logger.debug.call_args.args[1]
        assert "*****" in dumped
        assert "hunter2" not in dumped
        assert "secret-token" not in dumped
        assert "secret-chat" not in dumped
        # The real config is untouched (masking works on a deepcopy).
        assert conf["password"] == "hunter2"
        assert conf["telegram"]["token"] == "secret-token"

    def test_debug_without_telegram_section_ok(self) -> None:
        conf = self.make_conf(VALID_CONFIG.replace("logLevel: INFO", "logLevel: DEBUG"))
        assert conf["logLevel"] == "DEBUG"
        self.logger.debug.assert_called_once()

    def test_debug_dump_survives_non_json_yaml_types(self) -> None:
        # An unquoted date is loaded by YAML as a datetime.date, which
        # json.dumps cannot serialize without default=str.
        text = VALID_CONFIG.replace("logLevel: INFO", "logLevel: DEBUG")
        text += "someDate: 2026-07-16\n"
        self.make_conf(text)
        self.logger.debug.assert_called_once()
        assert "2026-07-16" in self.logger.debug.call_args.args[1]


if __name__ == "__main__":
    unittest.main()
