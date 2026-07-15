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
        actions: [move, mark_as_read]
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
        self.logger.error.assert_called_once()


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

    def test_falsy_value_treated_as_missing(self) -> None:
        self.assert_exits(VALID_CONFIG.replace("port: 993", "port: 0"))
        assert "port" in self.logger.critical.call_args.args

    def test_unknown_filter_category_exits(self) -> None:
        self.assert_exits(VALID_CONFIG.replace("  subject:", "  bogus:"))
        assert "bogus" in self.logger.critical.call_args.args

    def test_filter_entry_missing_pattern_exits(self) -> None:
        self.assert_exits(VALID_CONFIG.replace("- pattern: '[SPAM]'", "- weight: 3"))
        assert "pattern" in self.logger.critical.call_args.args

    def test_filter_entry_missing_actions_exits(self) -> None:
        self.assert_exits(
            VALID_CONFIG.replace("        actions: [move, mark_as_read]", "")
        )
        assert "actions" in self.logger.critical.call_args.args


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


if __name__ == "__main__":
    unittest.main()
