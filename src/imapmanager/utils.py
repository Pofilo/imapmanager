"""
utils.py: useful and general methods for imapmanager.

imapmanager: Connect and manage your mail account through IMAP.
Copyright (C) pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms
of the GNU General Public License as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import re
from email.header import decode_header, make_header


def extract_and_sanitize_mail_addresses(addresses: str) -> list[str]:
    """
    Extract and sanitize all mail addresses in a string.
    "Name LASTNAME" <Name.Lastname@example.com>, YES.NO@may.be, toto@example.com
    will become a list containing:
    name.lastname@example.com, yes.no@may.be, toto@example.com
    :param      addresses   the mail addresses to clean.
    """
    # If the string is empty, we cannot find any mails
    if not addresses:
        return None

    # Regex for a mail address
    regex = r"([\w0-9._+-]+@[\w0-9._-]+\.[\w0-9_-]+)"
    # Extract all mail address in a list
    addresses = re.findall(regex, addresses, re.MULTILINE | re.IGNORECASE)
    # Lower-case each address, keeping input order and dropping duplicates
    return list(dict.fromkeys(x.lower() for x in addresses))


def decode_subject(subject: str) -> str:
    """
    Decode an email subject that may contain RFC 2047 encoded-words.
    """
    if not subject:
        return None

    return str(make_header(decode_header(subject))).replace("\n", " ")
