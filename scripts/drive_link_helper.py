#!/usr/bin/env python3
"""Print or set Google Drive file IDs in Drive-Links.csv.

Example — get link for a doc after uploading to Drive:
  python scripts/drive_link_helper.py show MKT-SW-SILO

Example — set file ID from a share URL:
  python scripts/drive_link_helper.py set MKT-SW-SILO 1ABCdefGHIjkL_MnOpQrStUvWxYz

Share URL format: https://drive.google.com/file/d/FILE_ID/view
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "knowledge-base" / "sheets" / "Drive-Links.csv"

_FILE_ID_RE = re.compile(r"/file/d/([a-zA-Z0-9_-]+)")


def _read_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_rows(rows: list[dict[str, str]]) -> None:
    fieldnames = ["doc_id", "drive_file_id", "drive_url", "notes"]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _extract_file_id(value: str) -> str:
    value = value.strip()
    match = _FILE_ID_RE.search(value)
    return match.group(1) if match else value


def cmd_show(doc_id: str) -> int:
    from agent.drive_links import resolve_for_document
    from agent.knowledge_retriever import KnowledgeBase

    kb = KnowledgeBase()
    doc = next((d for d in kb._documents if d.doc_id == doc_id), None)
    if not doc:
        print(f"Unknown doc_id: {doc_id}")
        return 1
    print(f"{doc_id}: {doc.title}")
    print(f"URL: {resolve_for_document(doc_id, doc.local_path)}")
    return 0


def cmd_set(doc_id: str, file_id_or_url: str) -> int:
    file_id = _extract_file_id(file_id_or_url)
    rows = _read_rows()
    found = False
    for row in rows:
        if row.get("doc_id") == doc_id:
            row["drive_file_id"] = file_id
            row["drive_url"] = ""
            found = True
            break
    if not found:
        rows.append({"doc_id": doc_id, "drive_file_id": file_id, "drive_url": "", "notes": ""})
    _write_rows(rows)
    print(f"Set {doc_id} -> https://drive.google.com/file/d/{file_id}/view")
    return 0


def cmd_list() -> int:
    from agent.knowledge_retriever import KnowledgeBase

    kb = KnowledgeBase()
    for doc in kb._documents:
        status = "direct" if "/file/d/" in doc.drive_url else "search/folder"
        print(f"{doc.doc_id:20} [{status:14}] {doc.drive_url}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 0
    command = sys.argv[1].lower()
    if command == "list":
        return cmd_list()
    if command == "show" and len(sys.argv) >= 3:
        return cmd_show(sys.argv[2])
    if command == "set" and len(sys.argv) >= 4:
        return cmd_set(sys.argv[2], sys.argv[3])
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
