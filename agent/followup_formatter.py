"""Build customer follow-up email from parsed meeting summary."""

from __future__ import annotations

from agent.knowledge_retriever import RetrievalResult
from agent.payload import OpportunityNotePayload


def _contact(payload: OpportunityNotePayload) -> str:
    return payload.contact_name.strip() or "there"


def _rep_name(payload: OpportunityNotePayload) -> str:
    return payload.sales_rep_full_name.strip() or payload.sales_rep.strip() or "Sales Team"


def _rep_email(payload: OpportunityNotePayload) -> str:
    return payload.sales_rep_email.strip() or "sales@unifiedcloudsensors.eu"


def _meeting_display(payload: OpportunityNotePayload) -> str:
    if payload.meeting_date_display.strip():
        return payload.meeting_date_display.strip()
    return payload.meeting_date


def _roadmap(payload: OpportunityNotePayload) -> list[str]:
    items: list[str] = []
    topics = (payload.discussion_topics + " " + payload.notes).lower()
    company = payload.company

    if any(k in topics for k in ("ucs-x3", "diniargeo", "laumas")):
        items.append("⚙️ Implementation of UCS-X3 on DiniArgeo + UCS-X3 Laumas")

    if "camera" in topics:
        items.append(
            f"📷 SW implementation of the camera system — we will provide the PC and cameras, "
            f"{company} will handle the installation"
        )

    if payload.required_summary.strip():
        prep = payload.required_summary.replace("Certificate D, price list, marketing materials", "")
        prep = payload.required_summary
        if "certificate" in prep.lower():
            items.append("📄 I will prepare for you: Certificate D, a price list, and marketing materials")
        else:
            items.append(f"📄 I will prepare for you: {prep}")
    elif payload.required_items.strip():
        items.append("📄 I will prepare for you: Certificate D, a price list, and marketing materials")

    scales = payload.scales_per_year.strip()
    if scales or "slovakia" in topics:
        count = scales or "10"
        items.append(
            f"🇸🇰 Slovakia — you see a potential of {count} scales per year. "
            "Let's discuss how I can help you with the clients"
        )

    return items


def build_followup_subject(payload: OpportunityNotePayload) -> str:
    return f"Follow-up: {payload.company} — meeting {_meeting_display(payload)}"


def build_followup_plain(payload: OpportunityNotePayload, retrieval: RetrievalResult) -> str:
    contact = _contact(payload)
    rep = _rep_name(payload)
    rep_email = _rep_email(payload)
    date_label = _meeting_display(payload)
    topics = (payload.discussion_topics + payload.notes).lower()

    lines = [
        f"Hi {contact},",
        "",
        (
            f"It was a pleasure meeting with you and your colleague on {date_label} "
            f"to discuss the system implementation options. I see really great potential in this "
            f"and look forward to our cooperation!"
        ),
        "",
    ]

    if any(k in topics for k in ("pricing", "price", "quote", "certificate")):
        lines.extend([
            "As a first step, I am sending you the final price quote in the attachment — "
            "exactly as we agreed.",
            "",
        ])

    if payload.extra_news.strip():
        news = payload.extra_news.strip().replace(" - ", " — ")
        lines.extend([
            "A little bit of extra news 🎉",
            news,
            "",
        ])

    roadmap = _roadmap(payload)
    if roadmap:
        lines.append("What lies ahead of us:")
        lines.extend(roadmap)
        lines.append("")

    lines.extend([
        "Would you have time for a short meeting next week? I would like to go through the offer together, "
        "answer any questions, and agree on the next steps.",
        "",
        "Let me know which date and time works best for you.",
        "",
        "Best regards,",
        "",
        rep,
        "Unified Cloud Sensors",
        rep_email,
    ])
    return "\n".join(lines)


def build_followup_html(payload: OpportunityNotePayload, retrieval: RetrievalResult) -> str:
    plain = build_followup_plain(payload, retrieval)
    subject = build_followup_subject(payload)
    body = plain.replace("\n\n", "</p><p>").replace("\n", "<br>")
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{subject}</title></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #222; max-width: 640px;">
  <p>{body}</p>
</body>
</html>"""
