"""
utils.py: useful and general methods for imapmanager.

imapmanager: Connect and manage your mail account through IMAP.
Copyright (C) pofilo <git@pofilo.fr>

This program is free software: you can redistribute it and/or modify it under the terms
of the GNU General Public License as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANYWARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import base64
import logging
import quopri
import re


logger = logging.getLogger("imapmanager")


def extract_and_sanitize_mail_addresses(addresses):
    """
    Extract and sanitize all mail addresses in a string.
    "Name LASTNAME" <Name.Lastname@example.com>, YES.NO@may.be, toto@example.com
    will become a list containing:
    name.lastname@example.com, yes.no@may.be, toto@example.com
    :param      addresses   the mail addresses to clean
    """

    # If the string is empty, we cannot find any mails
    if not addresses:
        return None

    # Regex for a mail address
    regex = r"([\w0-9._-]+@[\w0-9._-]+\.[\w0-9_-]+)"
    # Extract all mail address in a list
    addresses = re.findall(regex, addresses, re.M | re.I)
    # Lower each mail address
    addresses = [x.lower() for x in addresses]

    return addresses


def decode_subject(subject):
    """
    Credits: https://stackoverflow.com/a/43393449
    """
    pattern = re.compile(
        r"(([^=]*)=\?([^\?]*)\?([BbQq])\?([^\?]*)\?=([^=]*))", re.IGNORECASE
    )
    data = pattern.findall(subject)
    line = []
    if data:
        for g in data:
            (_raw, extra1, encoding, method, string, extra) = g
            extra1 = extra1.replace("\r", "").replace("\n", "").strip()
            if len(extra1) > 0:
                line.append(extra1)
            if method.lower() == "q":
                string = quopri.decodestring(string)
                string = string.decode(encoding, errors="ignore")
                string = string.replace("_", " ").strip()
            if method.lower() == "b":
                string = base64.b64decode(string)
                string = string.decode(encoding, errors="ignore")
            line.append(string)
            extra = extra.replace("\r", "").replace("\n", "").strip()
            if len(extra) > 0:
                line.append(extra)
        subject = "".join(line)

    return subject
