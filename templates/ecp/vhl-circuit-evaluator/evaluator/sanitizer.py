"""
Sanitizer module: robust ANSI escape code and terminal sequence stripper.
"""

from __future__ import annotations

import re
from typing import List

ANSI_REGEX = re.compile(
    r"""
    \x1b              # ESC
    (?:               # 7-bit C1 Fe
        [@-Z\\-_]
    |                 # or [ Control Sequence Introducer
        \[
        [0-?]*        # Parameter Bytes
        [ -/]*        # Intermediate Bytes
        [@-~]         # Final Byte
    )
    """,
    re.VERBOSE,
)


def sanitize_ansi(raw_text: str) -> str:
    """Strips ANSI escape codes, cursor positioning, and terminal styling."""
    if not raw_text:
        return ""
    clean = ANSI_REGEX.sub("", raw_text)
    clean = clean.replace("\r\n", "\n").replace("\r", "\n")
    return clean


def sanitize_lines(raw_lines: List[str]) -> List[str]:
    """Strips ANSI sequences and whitespace, filtering empty lines."""
    cleaned = []
    for line in raw_lines:
        s = sanitize_ansi(line).strip()
        if s:
            cleaned.append(s)
    return cleaned
