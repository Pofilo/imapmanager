"""
Unit tests for imapmanager.utils.
"""

import unittest

from imapmanager.utils import decode_subject, extract_and_sanitize_mail_addresses


class TestExtractAndSanitizeMailAddresses(unittest.TestCase):
    def test_none_input_returns_none(self) -> None:
        assert extract_and_sanitize_mail_addresses(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert extract_and_sanitize_mail_addresses("") is None

    def test_single_address_lowercased(self) -> None:
        assert extract_and_sanitize_mail_addresses("John.DOE@Example.COM") == [
            "john.doe@example.com"
        ]

    def test_display_name_angle_brackets(self) -> None:
        assert extract_and_sanitize_mail_addresses(
            '"Name LASTNAME" <Name.Lastname@example.com>'
        ) == ["name.lastname@example.com"]

    def test_multiple_addresses_preserve_order(self) -> None:
        assert extract_and_sanitize_mail_addresses(
            '"Name LASTNAME" <Name.Lastname@example.com>, YES.NO@may.be, '
            "toto@example.com"
        ) == ["name.lastname@example.com", "yes.no@may.be", "toto@example.com"]

    def test_duplicates_deduped_case_insensitively(self) -> None:
        assert extract_and_sanitize_mail_addresses("A@x.com, a@X.com, b@x.com") == [
            "a@x.com",
            "b@x.com",
        ]

    def test_no_address_returns_empty_list(self) -> None:
        # A non-empty string without any address gives an empty list, not None.
        assert extract_and_sanitize_mail_addresses("no address here") == []


class TestDecodeSubject(unittest.TestCase):
    def test_none_returns_none(self) -> None:
        assert decode_subject(None) is None

    def test_empty_returns_none(self) -> None:
        assert decode_subject("") is None

    def test_plain_ascii_passthrough(self) -> None:
        assert decode_subject("Hello world") == "Hello world"

    def test_rfc2047_encoded_word(self) -> None:
        # "Prix cassés" encoded as RFC 2047 base64 utf-8
        assert decode_subject("=?utf-8?b?UHJpeCBjYXNzw6lz?=") == "Prix cassés"

    def test_newlines_replaced_by_spaces(self) -> None:
        assert decode_subject("line one\nline two") == "line one line two"


if __name__ == "__main__":
    unittest.main()
