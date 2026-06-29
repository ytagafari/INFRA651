"""Build PDF attachments from matched knowledge-base documents."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path

from agent.knowledge_retriever import Document

ROOT = Path(__file__).resolve().parents[1]

MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".mp4": "video/mp4",
}

_TYPE_PRIORITY = {"price_list": 0, "marketing": 1, "datasheet": 2, "certification": 3, "video": 9}


@dataclass
class EmailAttachment:
    filename: str
    mime_type: str
    content_base64: str
    size_bytes: int
    doc_id: str = ""


def _attach_enabled() -> bool:
    value = os.environ.get("ATTACH_PDF_FILES", "1").strip().lower()
    return value in ("1", "true", "yes")


def _max_files() -> int:
    try:
        return max(1, int(os.environ.get("EMAIL_MAX_ATTACHMENTS", "4")))
    except ValueError:
        return 4


def _max_total_bytes() -> int:
    try:
        return max(500_000, int(os.environ.get("EMAIL_MAX_ATTACHMENT_BYTES", "20000000")))
    except ValueError:
        return 20_000_000


def _dedupe_documents(documents: list[Document]) -> list[Document]:
    seen: set[str] = set()
    unique: list[Document] = []
    for doc in sorted(documents, key=lambda d: d.score, reverse=True):
        if doc.doc_id in seen:
            continue
        seen.add(doc.doc_id)
        unique.append(doc)
    return unique


def _sort_for_attachments(documents: list[Document]) -> list[Document]:
    unique = _dedupe_documents(documents)
    return sorted(
        unique,
        key=lambda d: (_TYPE_PRIORITY.get(d.doc_type, 5), -d.score),
    )


def resolve_local_file(local_path: str) -> Path | None:
    path = ROOT / local_path.replace("\\", "/")
    return path if path.is_file() else None


def build_attachments_from_documents(
    documents: list[Document],
    *,
    pdf_only: bool = True,
) -> tuple[list[EmailAttachment], list[str]]:
    """Return attachments and notes (skipped file names / reasons)."""
    if not _attach_enabled():
        return [], ["PDF attachments disabled (ATTACH_PDF_FILES=0)"]

    max_files = _max_files()
    max_bytes = _max_total_bytes()
    attachments: list[EmailAttachment] = []
    notes: list[str] = []
    total = 0

    for doc in _sort_for_attachments([d for d in documents if d.score > 0]):
        if len(attachments) >= max_files:
            notes.append(f"Skipped extra files after {max_files} attachments (Gmail size limit)")
            break

        path = resolve_local_file(doc.local_path)
        if not path:
            notes.append(f"Not on server: {Path(doc.local_path).name}")
            continue

        ext = path.suffix.lower()
        if pdf_only and ext != ".pdf":
            continue

        size = path.stat().st_size
        if total + size > max_bytes:
            notes.append(f"Skipped {path.name} (would exceed {max_bytes // 1_000_000} MB limit)")
            continue

        mime = MIME_BY_EXT.get(ext, "application/octet-stream")
        attachments.append(
            EmailAttachment(
                filename=path.name,
                mime_type=mime,
                content_base64=base64.b64encode(path.read_bytes()).decode("ascii"),
                size_bytes=size,
                doc_id=doc.doc_id,
            )
        )
        total += size

    return attachments, notes


def build_attachments_for_retrieval(retrieval_documents: list[Document]) -> list[EmailAttachment]:
    attachments, _ = build_attachments_from_documents(retrieval_documents)
    return attachments


def attachments_for_webapp(attachments: list[EmailAttachment]) -> list[dict[str, str]]:
    return [
        {
            "filename": item.filename,
            "mimeType": item.mime_type,
            "content": item.content_base64,
        }
        for item in attachments
    ]


def document_exists(local_path: str) -> bool:
    return resolve_local_file(local_path) is not None
