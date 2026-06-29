"""Build a customer-ready sales email with products, pricing, and matched documents."""

from __future__ import annotations

import re
from datetime import datetime

from agent.knowledge_retriever import Document, PriceEntry, Product, RetrievalResult
from agent.payload import OpportunityNotePayload

EMAIL_FORMAT_VERSION = "sales-response-v1"


def _contact(payload: OpportunityNotePayload) -> str:
    return payload.contact_name.strip() or "there"


def _rep_name(payload: OpportunityNotePayload) -> str:
    return payload.sales_rep_full_name.strip() or payload.sales_rep.strip() or "Sales Team"


def _rep_email(payload: OpportunityNotePayload) -> str:
    return payload.sales_rep_email.strip() or "sales@unifiedcloudsensors.eu"


def _meeting_date_long(iso_date: str) -> str:
    try:
        dt = datetime.strptime(iso_date.strip()[:10], "%Y-%m-%d")
        return dt.strftime("%B %d, %Y").replace(" 0", " ")
    except ValueError:
        return iso_date


def _dedupe_documents(documents: list[Document]) -> list[Document]:
    seen: set[str] = set()
    unique: list[Document] = []
    for doc in sorted(documents, key=lambda d: d.score, reverse=True):
        if doc.doc_id in seen:
            continue
        seen.add(doc.doc_id)
        unique.append(doc)
    return unique


def _doc_label(doc: Document) -> str:
    type_labels = {
        "marketing": "Marketing",
        "price_list": "Pricing",
        "datasheet": "Datasheet",
        "certificate": "Certificate",
        "video": "Video",
    }
    kind = type_labels.get(doc.doc_type, doc.doc_type.replace("_", " ").title())
    return f"{doc.title} ({kind})"


def _solution_intro(payload: OpportunityNotePayload) -> str:
    topics = f"{payload.discussion_topics} {payload.notes or ''}".lower()
    if "silo" in topics or "grain" in topics or "agriculture" in topics:
        count = ""
        match = re.search(r"(\d+)\s+(?:grain\s+)?silos?", payload.notes or "", re.I)
        if match:
            count = f" for your {match.group(1)} silo sites"
        return (
            f"Following our discussion about silo monitoring{count}, "
            "below is the recommended UCS solution, SaaS pricing, and the documents you requested."
        )
    if any(k in topics for k in ("truck scale", "weighbridge", "m740")):
        return (
            "Following our discussion about truck scale digitalization, "
            "below is the recommended hardware, pricing, and supporting documentation."
        )
    if any(k in topics for k in ("belt scale", "conveyor")):
        return (
            "Following our discussion about belt scale monitoring, "
            "below is the recommended SensWEIGHT solution and pricing."
        )
    return (
        f"Following our meeting, below is the recommended UCS solution, "
        f"pricing, and documents based on: {payload.discussion_topics}."
    )


def _product_bullets(products: list[Product], payload: OpportunityNotePayload) -> list[str]:
    if not products:
        return [
            "• **SensWEIGHT platform** — remote IIoT monitoring with UCS CLOUD dashboard and alerts."
        ]

    topics = f"{payload.discussion_topics} {payload.notes or ''}".lower()
    bullets: list[str] = []
    for product in products[:4]:
        line = f"• **{product.product_name}** — {product.description}"
        if product.product_id.startswith("UCS-X") and any(k in topics for k in ("ucx3", "ucs-x3", "x3")):
            line += " (recommended gateway for UCX3-class connectivity)."
        bullets.append(line)
    return bullets


def _pricing_lines(prices: list[PriceEntry]) -> list[str]:
    if not prices:
        return []
    lines = ["**SensWEIGHT SaaS pricing** (per device/month)", ""]
    for price in prices[:6]:
        lines.append(f"• **{price.list_price_eur} {price.currency}** — {price.price_tier or price.sku}")
        if price.notes.strip():
            lines.append(f"  {price.notes}")
    return lines


def _document_lines(documents: list[Document], attached_names: list[str] | None = None) -> list[str]:
    docs = _dedupe_documents([d for d in documents if d.score > 0])[:8]
    if attached_names:
        lines = ["**Attached PDF files** (see email attachments)", ""]
        for name in attached_names:
            lines.append(f"• {name}")
        return lines
    if not docs:
        return []
    lines = ["**Documents (click to open in Google Drive)**", ""]
    for doc in docs:
        lines.append(f"• {_doc_label(doc)}")
        lines.append(f"  {doc.drive_url}")
    return lines


def _next_steps(payload: OpportunityNotePayload, retrieval: RetrievalResult) -> list[str]:
    topics = f"{payload.discussion_topics} {payload.notes or ''}".lower()
    steps = ["**Proposed next steps**", ""]
    if "silo" in topics:
        steps.append("1. Review the SensWEIGHT silo leaflet and confirm phase-1 rollout scope.")
        steps.append("2. Choose a SaaS tier (Basic for monitoring, Advanced for diagnostics).")
        steps.append("3. Schedule a short call to finalize the commercial offer.")
    elif "pricing" in topics or "saas" in topics:
        steps.append("1. Review the attached SaaS pricing PDF.")
        steps.append("2. Confirm device count and required monitoring features.")
        steps.append("3. Agree on subscription tier and project timeline.")
    else:
        steps.append("1. Review the attached documents.")
        steps.append("2. Confirm scope and technical requirements.")
        steps.append("3. Schedule a follow-up call to finalize the offer.")
    return steps


def build_sales_response_subject(payload: OpportunityNotePayload, retrieval: RetrievalResult) -> str:
    topics = payload.discussion_topics.lower()
    focus = "SensWEIGHT solution"
    if "silo" in topics:
        focus = "SensSILO / SensWEIGHT silo monitoring"
    elif "truck" in topics:
        focus = "truck scale digitalization"
    return f"Follow-up: {payload.company} — {focus} & pricing"


def build_sales_response_plain(
    payload: OpportunityNotePayload,
    retrieval: RetrievalResult,
    attached_names: list[str] | None = None,
) -> str:
    contact = _contact(payload)
    rep = _rep_name(payload)
    rep_email = _rep_email(payload)
    date_long = _meeting_date_long(payload.meeting_date)

    lines = [
        f"Hi {contact},",
        "",
        f"Thank you for meeting with us on {date_long}.",
        _solution_intro(payload),
        "",
        "**Recommended solution**",
        "",
    ]
    lines.extend(_product_bullets(retrieval.products, payload))
    lines.append("")

    pricing = _pricing_lines(retrieval.prices)
    if pricing:
        lines.extend(pricing)
        lines.append("")

    docs = _document_lines(retrieval.documents, attached_names)
    if docs:
        lines.extend(docs)
        lines.append("")

    if payload.notes.strip():
        lines.extend(["**Your requirements (from our meeting)**", "", f"• {payload.notes.strip()}", ""])

    lines.extend(_next_steps(payload, retrieval))
    lines.extend([
        "",
        "Please let me know if you have any questions, or suggest a time for a short follow-up call next week.",
        "",
        "Best regards,",
        "",
        rep,
        "Unified Cloud Sensors",
        rep_email,
    ])
    return "\n".join(lines)


def build_sales_response_html(
    payload: OpportunityNotePayload,
    retrieval: RetrievalResult,
    attached_names: list[str] | None = None,
) -> str:
    subject = build_sales_response_subject(payload, retrieval)
    contact = _contact(payload)
    rep = _rep_name(payload)
    rep_email = _rep_email(payload)
    date_long = _meeting_date_long(payload.meeting_date)

    products_html = "".join(
        f"<li><strong>{p.product_name}</strong> — {p.description}</li>"
        for p in retrieval.products[:4]
    ) or "<li><strong>SensWEIGHT platform</strong> — remote IIoT monitoring with UCS CLOUD.</li>"

    prices_html = "".join(
        f"<li><strong>{pr.list_price_eur} {pr.currency}</strong> — {pr.price_tier or pr.sku}"
        f"{(' — ' + pr.notes) if pr.notes else ''}</li>"
        for pr in retrieval.prices[:6]
    )

    if attached_names:
        docs_html = "".join(f"<li>{name}</li>" for name in attached_names)
        docs_section = f"<h3>Attached PDF files</h3><ul>{docs_html}</ul>"
    else:
        docs = _dedupe_documents([d for d in retrieval.documents if d.score > 0])[:8]
        docs_html = "".join(
            f'<li><a href="{d.drive_url}" style="color:#1a73e8;">{_doc_label(d)}</a></li>'
            for d in docs
        )
        docs_section = f"<h3>Documents (Google Drive)</h3><ul>{docs_html}</ul>" if docs_html else ""

    steps_html = "".join(f"<li>{s}</li>" for s in _next_steps(payload, retrieval)[2:])

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{subject}</title></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #222; max-width: 720px;">
  <p>Hi {contact},</p>
  <p>Thank you for meeting with us on {date_long}. {_solution_intro(payload)}</p>
  <h3>Recommended solution</h3>
  <ul>{products_html}</ul>
  {"<h3>SensWEIGHT SaaS pricing</h3><ul>" + prices_html + "</ul>" if prices_html else ""}
  {docs_section}
  {"<h3>Your requirements</h3><p>" + payload.notes.strip() + "</p>" if payload.notes.strip() else ""}
  <h3>Proposed next steps</h3>
  <ol>{steps_html}</ol>
  <p>Please let me know if you have any questions, or suggest a time for a short follow-up call next week.</p>
  <p>Best regards,<br><strong>{rep}</strong><br>Unified Cloud Sensors<br>{rep_email}</p>
</body>
</html>"""
