"""Build UCS AI-style meeting summary output from CRM input."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from agent.knowledge_retriever import RetrievalResult
from agent.payload import OpportunityNotePayload

EMAIL_FORMAT_VERSION = "ucs-ai-v1"


def _contact_name(payload: OpportunityNotePayload) -> str:
    if payload.contact_name.strip():
        return payload.contact_name.strip()
    match = re.search(r"contact:\s*([^\n,;]+)", payload.notes or "", re.I)
    return match.group(1).strip() if match else ""


def _meeting_date_long(iso_date: str) -> str:
    try:
        dt = datetime.strptime(iso_date.strip()[:10], "%Y-%m-%d")
        return dt.strftime("%B %d, %Y").replace(" 0", " ")
    except ValueError:
        return iso_date


def _generated_stamp() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%B %d, %Y, %H:%M").replace(" 0", " ")


def _combined_text(payload: OpportunityNotePayload) -> str:
    return f"{payload.discussion_topics} {payload.notes or ''}".lower()


def _scale_potential(notes: str) -> str:
    match = re.search(r"(\d+)\s*scales?\s*(?:per\s*year|/year|yearly)?", notes, re.I)
    return f"{match.group(1)} scales per year" if match else ""


def _has_topic(topics: str, *terms: str) -> bool:
    return any(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", topics) for term in terms)


def _implementation_label(topics: str) -> str:
    parts: list[str] = []
    if _has_topic(topics, "laumas", "m500"):
        parts.append("Laumas")
    if _has_topic(topics, "diniargeo", "ucs-x3", "ucx3"):
        parts.append("UCS-X3 on DiniArgeo")
    return " and ".join(parts) if parts else "system integration discussed"


def _required_information(payload: OpportunityNotePayload, retrieval: RetrievalResult) -> list[str]:
    topics = _combined_text(payload)
    items: list[str] = []

    if any(k in topics for k in ("certificate d", "certificate", "cert")):
        items.append("Certificate D from Laumas")
        if any(k in topics for k in ("pricing", "price", "quote")):
            items.append("Price list for the certificate")

    if any(k in topics for k in ("camera", "vision", "computer")):
        items.append("Cameras + computer -> Ryant")

    if any(k in topics for k in ("marketing", "leaflet", "brochure")):
        lang = " (EN+SK)" if any(k in topics for k in ("sk", "slovak", "slovakia")) else ""
        items.append(f"Marketing materials (UCS + {payload.company}) -> HTML leaflets{lang}")

    if _has_topic(topics, "ai", "recommendation", "model"):
        items.append(
            f"AI skills for {payload.company}; with a recommendation on which AI model to use"
        )

    if any(k in topics for k in ("laumas", "modbus", "documentation", "protocol", "m500")):
        items.append(
            "Laumas documentation (computer protocol, Modbus protocol, calibration, "
            "technical manuals, ideally a video)"
        )

    if any(k in topics for k in ("pricing", "price", "quote", "saas")) and not any(
        "price list for the certificate" in i.lower() for i in items
    ):
        items.append("Price list and commercial offer")

    if not items and payload.notes.strip():
        items.append(payload.notes.strip())

    return items


def _build_summary(payload: OpportunityNotePayload) -> str:
    contact = _contact_name(payload) or "the customer contact"
    rep = payload.sales_rep or "the sales representative"
    date_long = _meeting_date_long(payload.meeting_date)
    topics = _combined_text(payload)

    focus_parts: list[str] = []
    if "laumas" in topics or "m500" in topics:
        focus_parts.append("the Laumas system")
    if "camera" in topics:
        focus_parts.append("a camera system")
    focus = " and ".join(focus_parts) if focus_parts else payload.discussion_topics.strip()

    promise = ""
    if "diniargeo" in topics or "ucs-x3" in topics:
        promise = (
            f" {contact} promised the implementation of UCS-X3 on DiniArgeo and emphasized "
            "the need to deliver various information and materials for the successful execution of the project."
        )
    else:
        promise = (
            f" The team reviewed next steps and the information and materials needed "
            "for successful project execution."
        )

    return (
        f"On {date_long}, a meeting took place between {contact}, a colleague, and {rep}, "
        f"where they discussed the implementation of {focus}.{promise}"
    )


def _key_points(payload: OpportunityNotePayload) -> list[str]:
    topics = _combined_text(payload)
    contact = _contact_name(payload) or "The contact"
    date_long = _meeting_date_long(payload.meeting_date)
    points = [f"📅 Meeting Date: {date_long}"]

    impl = _implementation_label(topics)
    if impl:
        points.append(f"💻 Implementation: {impl}")

    if "camera" in topics:
        points.append("📷 Camera System: Focus on SW implementation, not selling HW")
        points.append(
            f"🔧 Delivery: Computer and cameras, {payload.company} will handle the installation"
        )

    required_bits: list[str] = []
    if any(k in topics for k in ("certificate", "cert")):
        required_bits.append("Certificate D")
    if any(k in topics for k in ("pricing", "price", "quote")):
        required_bits.append("price list")
    if any(k in topics for k in ("marketing", "leaflet")):
        required_bits.append("marketing materials")
    if any(k in topics for k in ("ai", "recommendation")):
        required_bits.append("AI skills")
    if required_bits:
        points.append(f"📄 Required Information: {', '.join(required_bits)}")

    potential = _scale_potential(payload.notes or "")
    if potential or "slovakia" in topics:
        region = " in Slovakia" if "slovakia" in topics else ""
        who = contact if _contact_name(payload) else payload.company
        if potential:
            points.append(
                f"📈 Potential: {who} sees a potential of {potential}, "
                f"but needs help with clients{region}"
            )
        else:
            points.append(f"📈 Potential: Growth opportunity{region} with partner support needed")

    return points


def _detail_paragraphs(payload: OpportunityNotePayload) -> list[str]:
    topics = _combined_text(payload)
    contact = _contact_name(payload) or "The contact"
    rep = payload.sales_rep or "Nikola"
    company = payload.company
    paragraphs: list[str] = []

    if "laumas" in topics or "m500" in topics:
        paragraphs.append(
            f"The {company} team is ready for the Laumas implementation; they are very well "
            "acquainted with the system via M500."
        )

    if "diniargeo" in topics or "ucs-x3" in topics:
        paragraphs.append(
            f"{contact} promised me that he would also implement UCS-X3 on DiniArgeo; "
            "he will keep me updated."
        )

    if "camera" in topics:
        paragraphs.extend([
            f"We talked about the camera system; {rep} explained that our goal is not to sell HW, "
            "but rather SW implementation.",
            (
                f"{contact} sees the M500 scale as a good point for camera implementation; "
                f"we are to provide the computer and cameras; {company} will handle the mechanical "
                "and cable installation."
            ),
        ])

    if payload.extra_news.strip():
        paragraphs.append(payload.extra_news.strip())

    return paragraphs


def _section_header(payload: OpportunityNotePayload) -> str:
    contact = _contact_name(payload) or "Contact"
    rep = payload.sales_rep or "Sales Rep"
    date_long = _meeting_date_long(payload.meeting_date)
    return f"{date_long} {payload.company}: {contact}, Colleague & {rep}"


def build_email_subject(payload: OpportunityNotePayload) -> str:
    date_long = _meeting_date_long(payload.meeting_date)
    return f"UCS AI Summary: {payload.company} - {date_long}"


def build_email_plain(payload: OpportunityNotePayload, retrieval: RetrievalResult) -> str:
    lines = [
        f"Generated by UCS AI, {_generated_stamp()}:",
        "",
        "Summary",
        _build_summary(payload),
        "",
        "Key Points:",
    ]
    lines.extend(_key_points(payload))
    lines.append(_section_header(payload))
    lines.append("")
    for paragraph in _detail_paragraphs(payload):
        lines.append(paragraph)
        lines.append("")

    required = _required_information(payload, retrieval)
    if required:
        lines.extend(["", "He needs the following information:", ""])
        lines.extend(required)

    potential = _scale_potential(payload.notes or "")
    topics = _combined_text(payload)
    contact = _contact_name(payload) or payload.company
    if potential:
        closing = f"{contact} has a potential of {potential}"
        if "slovakia" in topics:
            closing += ", but he is willing to help with clients in Slovakia."
        else:
            closing += "."
        lines.extend(["", closing])

    return "\n".join(lines)


def build_email_html(payload: OpportunityNotePayload, retrieval: RetrievalResult) -> str:
    subject = build_email_subject(payload)
    key_points = "".join(f"<li>{point}</li>" for point in _key_points(payload))
    details = "".join(f"<p>{p}</p>" for p in _detail_paragraphs(payload))
    required = _required_information(payload, retrieval)
    required_html = "".join(f"<li>{item}</li>" for item in required) if required else ""

    potential = _scale_potential(payload.notes or "")
    topics = _combined_text(payload)
    contact = _contact_name(payload) or payload.company
    closing = ""
    if potential:
        closing = f"<p>{contact} has a potential of {potential}"
        if "slovakia" in topics:
            closing += ", but he is willing to help with clients in Slovakia."
        else:
            closing += ".</p>"

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{subject}</title></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #222; max-width: 720px;">
  <p><em>Generated by UCS AI, {_generated_stamp()}:</em></p>
  <h2>Summary</h2>
  <p>{_build_summary(payload)}</p>
  <h2>Key Points</h2>
  <ul>{key_points}</ul>
  <h2>{_section_header(payload)}</h2>
  {details}
  {"<h3>He needs the following information:</h3><ul>" + required_html + "</ul>" if required_html else ""}
  {closing}
</body>
</html>"""
