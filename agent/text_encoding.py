"""Repair text that was UTF-8 misread as Windows code page (common PowerShell issue)."""

from __future__ import annotations


def repair_text(text: str) -> str:
    if not text:
        return text
    for encoding in ("cp1250", "cp1252", "latin-1"):
        try:
            fixed = text.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if fixed != text and "\ufffd" not in fixed:
            return fixed
    return text
