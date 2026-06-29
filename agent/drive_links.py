"""Resolve Google Drive URLs for knowledge-base documents."""

from __future__ import annotations

import csv
import os
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVE_LINKS_CSV = ROOT / "knowledge-base" / "sheets" / "Drive-Links.csv"

_FILE_VIEW = "https://drive.google.com/file/d/{file_id}/view?usp=sharing"


def _filename_from_local_path(local_path: str) -> str:
    return Path(local_path.replace("\\", "/")).name


def build_drive_url(
    *,
    local_path: str,
    drive_file_id: str = "",
    drive_url: str = "",
) -> str:
    """Return a clickable Google Drive URL for a document."""
    if drive_url.strip():
        return drive_url.strip()
    if drive_file_id.strip():
        return _FILE_VIEW.format(file_id=drive_file_id.strip())

    folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "").strip()
    filename = _filename_from_local_path(local_path)
    encoded = urllib.parse.quote(filename)
    if folder_id:
        return f"https://drive.google.com/drive/folders/{folder_id}?q={encoded}"
    return f"https://drive.google.com/drive/search?q={encoded}"


def load_drive_link_map() -> dict[str, dict[str, str]]:
    if not DRIVE_LINKS_CSV.is_file():
        return {}
    rows: dict[str, dict[str, str]] = {}
    with DRIVE_LINKS_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            doc_id = row.get("doc_id", "").strip()
            if doc_id:
                rows[doc_id] = {
                    "drive_file_id": row.get("drive_file_id", "").strip(),
                    "drive_url": row.get("drive_url", "").strip(),
                }
    return rows


def resolve_for_document(doc_id: str, local_path: str) -> str:
    link_map = load_drive_link_map()
    entry = link_map.get(doc_id, {})
    return build_drive_url(
        local_path=local_path,
        drive_file_id=entry.get("drive_file_id", ""),
        drive_url=entry.get("drive_url", ""),
    )
