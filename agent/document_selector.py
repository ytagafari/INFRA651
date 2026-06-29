"""Select relevant marketing, datasheet, certification, and pricing documents."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from agent.knowledge_retriever import Document, RetrievalResult, tokenize


@dataclass
class SelectedDocumentSet:
    documents: list[Document] = field(default_factory=list)
    by_type: dict[str, list[str]] = field(default_factory=dict)
    selection_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "documents": [asdict(d) for d in self.documents],
            "by_type": self.by_type,
            "selection_notes": self.selection_notes,
        }


def _topics_text(*parts: str) -> str:
    return " ".join(p.strip() for p in parts if p.strip()).lower()


def select_documents(
    retrieval: RetrievalResult,
    discussion_topics: str,
    notes: str = "",
    *,
    limit: int = 8,
) -> SelectedDocumentSet:
    topics = _topics_text(discussion_topics, notes)
    tokens = set(tokenize(topics))
    selected: list[Document] = []
    seen: set[str] = set()
    notes_out: list[str] = []

    def add(doc: Document, reason: str) -> None:
        if doc.doc_id in seen:
            return
        seen.add(doc.doc_id)
        selected.append(doc)
        notes_out.append(f"{doc.doc_id}: {reason}")

    for doc in retrieval.documents:
        add(doc, f"keyword match (score={doc.score:.1f})")

    ranked = sorted(retrieval.documents, key=lambda d: d.score, reverse=True)

    def best_of_type(doc_type: str) -> Document | None:
        for doc in ranked:
            if doc.doc_type == doc_type:
                return doc
        return None

    if any(k in tokens for k in ("pricing", "price", "saas", "subscription", "quote", "cost")):
        pl = best_of_type("price_list")
        if pl:
            add(pl, "pricing/SaaS mentioned")

    if any(k in tokens for k in ("m740", "datasheet", "load", "cell", "wdesk", "clm8", "digital")):
        for doc in ranked:
            if doc.doc_type == "datasheet":
                add(doc, "product/datasheet topic")
                break

    if any(k in tokens for k in ("certification", "cert", "oiml", "ce", "approval", "legal")):
        for doc in ranked:
            if doc.doc_type == "certification":
                add(doc, "certification/compliance topic")
                break

    if any(k in tokens for k in ("leaflet", "marketing", "brochure", "materials")) or not selected:
        for doc in ranked:
            if doc.doc_type == "marketing":
                add(doc, "marketing material for opportunity")
                break

    if not any(d.doc_type == "marketing" for d in selected):
        mkt = best_of_type("marketing")
        if mkt:
            add(mkt, "default marketing overview")

    by_type: dict[str, list[str]] = {}
    for doc in selected[:limit]:
        by_type.setdefault(doc.doc_type, []).append(doc.doc_id)

    return SelectedDocumentSet(
        documents=selected[:limit],
        by_type=by_type,
        selection_notes=notes_out[:limit + 3],
    )
