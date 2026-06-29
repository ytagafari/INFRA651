"""Build and persist structured client profiles (agent memory) for future interactions."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.credibility_assessor import CredibilityResult
    from agent.document_selector import SelectedDocumentSet
    from agent.knowledge_retriever import RetrievalResult
    from agent.payload import OpportunityNotePayload

ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = Path(__file__).resolve().parent / "profiles"


def company_slug(company: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")
    return slug[:60] or "unknown-company"


@dataclass
class ClientProfile:
    company: str
    company_slug: str
    first_seen: str
    last_updated: str
    industry: str
    credibility_score: int
    credibility_level: str
    products_discussed: list[str] = field(default_factory=list)
    topics_history: list[str] = field(default_factory=list)
    documents_sent: list[str] = field(default_factory=list)
    meeting_count: int = 0
    meeting_dates: list[str] = field(default_factory=list)
    notes_summary: str = ""
    sales_rep: str = ""
    sales_rep_email: str = ""
    next_actions: list[str] = field(default_factory=list)
    interaction_log: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _unique_extend(existing: list[str], new_items: list[str], limit: int = 20) -> list[str]:
    seen = set(existing)
    merged = list(existing)
    for item in new_items:
        key = item.strip()
        if key and key not in seen:
            seen.add(key)
            merged.append(key)
    return merged[:limit]


def _derive_next_actions(topics: str, notes: str, doc_ids: list[str]) -> list[str]:
    actions: list[str] = []
    text = f"{topics} {notes}".lower()
    if "pricing" in text or "saas" in text or any(d.startswith("PL-") for d in doc_ids):
        actions.append("Follow up with commercial offer and SaaS pricing")
    if any(d.startswith("MKT-") for d in doc_ids):
        actions.append("Share matched marketing leaflets with customer")
    if "cert" in text or "oiml" in text or any(d.startswith("CERT-") for d in doc_ids):
        actions.append("Provide certification pack for legal/compliance review")
    if not actions:
        actions.append("Schedule follow-up call with technical and commercial materials")
    return actions


def load_profile(slug: str, profiles_dir: Path | None = None) -> ClientProfile | None:
    path = (profiles_dir or PROFILES_DIR) / f"{slug}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ClientProfile(**data)


def save_profile(profile: ClientProfile, profiles_dir: Path | None = None) -> Path:
    out_dir = profiles_dir or PROFILES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{profile.company_slug}.json"
    path.write_text(json.dumps(profile.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def build_profile(
    payload: "OpportunityNotePayload",
    credibility: "CredibilityResult",
    retrieval: "RetrievalResult",
    selection: "SelectedDocumentSet",
    existing: ClientProfile | None = None,
) -> ClientProfile:
    now = datetime.now(timezone.utc).isoformat()
    slug = company_slug(payload.company)
    doc_ids = [d.doc_id for d in selection.documents]
    product_ids = [p.product_id for p in retrieval.products]
    topic_entry = payload.discussion_topics.strip()

    if existing:
        profile = existing
        profile.last_updated = now
        profile.meeting_count += 1
        profile.industry = credibility.industry or profile.industry
        profile.credibility_score = credibility.credibility_score
        profile.credibility_level = credibility.credibility_level
        profile.products_discussed = _unique_extend(profile.products_discussed, product_ids)
        profile.topics_history = _unique_extend(profile.topics_history, [topic_entry])
        profile.documents_sent = _unique_extend(profile.documents_sent, doc_ids)
        if payload.meeting_date and payload.meeting_date not in profile.meeting_dates:
            profile.meeting_dates.append(payload.meeting_date)
        if payload.notes.strip():
            profile.notes_summary = payload.notes.strip()[:500]
        if payload.sales_rep:
            profile.sales_rep = payload.sales_rep
        if payload.sales_rep_email:
            profile.sales_rep_email = payload.sales_rep_email
    else:
        profile = ClientProfile(
            company=payload.company,
            company_slug=slug,
            first_seen=payload.meeting_date or now[:10],
            last_updated=now,
            industry=credibility.industry,
            credibility_score=credibility.credibility_score,
            credibility_level=credibility.credibility_level,
            products_discussed=product_ids,
            topics_history=[topic_entry] if topic_entry else [],
            documents_sent=doc_ids,
            meeting_count=1,
            meeting_dates=[payload.meeting_date] if payload.meeting_date else [],
            notes_summary=payload.notes.strip()[:500],
            sales_rep=payload.sales_rep,
            sales_rep_email=payload.sales_rep_email,
        )

    profile.next_actions = _derive_next_actions(
        payload.discussion_topics,
        payload.notes,
        doc_ids,
    )
    profile.interaction_log.append(
        {
            "timestamp": now,
            "meeting_date": payload.meeting_date,
            "topics": payload.discussion_topics,
            "credibility_score": credibility.credibility_score,
            "documents": doc_ids,
        }
    )
    profile.interaction_log = profile.interaction_log[-20:]
    return profile
