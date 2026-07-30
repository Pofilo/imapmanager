"""
Unit tests for imapmanager.utils.
"""

import unittest

from imapmanager.utils import (
    decode_subject,
    extract_and_sanitize_mail_addresses,
    normalize_patterns,
)


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

    def test_plus_tag_subdomain_and_numeric_addresses(self) -> None:
        assert extract_and_sanitize_mail_addresses(
            "user+tag@example.com, user_name@sub.domain.example.com, 123@numbers.com"
        ) == [
            "user+tag@example.com",
            "user_name@sub.domain.example.com",
            "123@numbers.com",
        ]

    def test_special_characters_in_display_name(self) -> None:
        # Punctuation in the display name must not leak into the extracted address.
        assert extract_and_sanitize_mail_addresses(
            '"O\'Brien, John" <john.obrien@example.com>'
        ) == ["john.obrien@example.com"]

    def test_dots_and_dashes_in_domain(self) -> None:
        assert extract_and_sanitize_mail_addresses(
            "user.name@sub-domain.example-site.com"
        ) == ["user.name@sub-domain.example-site.com"]

    def test_surrounding_whitespace_ignored(self) -> None:
        assert extract_and_sanitize_mail_addresses(
            "  test1@example.com  ,  test2@example.com  "
        ) == ["test1@example.com", "test2@example.com"]


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

    def test_base64_utf8_decoded(self) -> None:
        assert decode_subject("=?UTF-8?B?VGVzdCBTdWJqZWN0?=") == "Test Subject"

    def test_quoted_printable_decoded(self) -> None:
        assert decode_subject("=?UTF-8?Q?Test=20Subject?=") == "Test Subject"

    def test_iso_8859_1_decoded(self) -> None:
        assert decode_subject("=?ISO-8859-1?Q?Caf=E9?=") == "Café"

    def test_windows_1252_decoded(self) -> None:
        assert decode_subject("=?windows-1252?Q?Test?=") == "Test"

    def test_base64_special_characters_decoded(self) -> None:
        # "Ééè" base64-encoded as UTF-8.
        assert decode_subject("=?UTF-8?B?w4nDqcOo?=") == "Ééè"

    def test_emoji_decoded(self) -> None:
        assert decode_subject("=?UTF-8?Q?Test_=F0=9F=98=80?=") == "Test 😀"

    def test_mixed_encoded_and_plain_text(self) -> None:
        assert decode_subject("Re: =?UTF-8?B?VGVzdA==?= message") == "Re: Test message"

    def test_multiple_encoded_words_joined(self) -> None:
        assert decode_subject("=?UTF-8?Q?Hello?= =?UTF-8?Q?_World?=") == "Hello World"

    def test_multiple_language_encodings(self) -> None:
        # Plain text plus two differently-encoded words in one subject.
        assert (
            decode_subject("English =?UTF-8?B?w6luw6c=?= =?ISO-8859-1?Q?test?=")
            == "English énçtest"
        )

    def test_long_subject_passthrough(self) -> None:
        long_text = "Very " * 50 + "long subject"
        assert decode_subject(long_text) == long_text

    def test_only_whitespace_preserved(self) -> None:
        assert decode_subject("   ") == "   "

    def test_badly_formed_encoded_word_does_not_crash(self) -> None:
        # An unterminated encoded-word must not raise; it is returned verbatim.
        assert decode_subject("=?UTF-8?Q?incomplete") == "=?UTF-8?Q?incomplete"


class TestNormalizePatterns(unittest.TestCase):
    def test_single_string_wrapped_in_a_list(self) -> None:
        assert normalize_patterns("[SPAM]") == ["[SPAM]"]

    def test_list_kept_in_order(self) -> None:
        assert normalize_patterns(["[SPAM]", "*** SPAM ***"]) == [
            "[SPAM]",
            "*** SPAM ***",
        ]

    def test_list_is_copied(self) -> None:
        patterns = ["[SPAM]"]
        result = normalize_patterns(patterns)
        result.append("other")
        assert patterns == ["[SPAM]"]


if __name__ == "__main__":
    unittest.main()
