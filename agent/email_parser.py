"""Parse a sales follow-up email into structured CRM payload fields."""

from __future__ import annotations

import re
from datetime import datetime

from agent.payload import OpportunityNotePayload

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

_TOPIC_KEYWORDS = [
    "Laumas",
    "UCS-X3",
    "DiniArgeo",
    "M500",
    "camera system",
    "Modbus",
    "certificate",
    "pricing",
    "marketing materials",
    "AI",
    "Slovakia",
    "scales",
    "SensSILO",
    "silo",
    "truck scale",
    "M740",
    "OIML",
    "SaaS",
]


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _parse_greeting_contact(text: str) -> str:
    match = re.search(r"^Hi\s+([^,\n]+),", text, re.I | re.M)
    return match.group(1).strip() if match else ""


def _parse_sales_rep(text: str) -> str:
    match = re.search(r"Best regards,?\s*\n+([^\n]+)", text, re.I)
    if match:
        return match.group(1).strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _parse_meeting_date(text: str, default_year: int = 2026) -> str:
    patterns = [
        r"on\s+([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?",
        r"([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        month_name = match.group(1).lower()
        day = int(match.group(2))
        year = int(match.group(3)) if match.group(3) else default_year
        month = _MONTHS.get(month_name)
        if month:
            return f"{year:04d}-{month:02d}-{day:02d}"
    return ""


def _parse_company(text: str) -> str:
    patterns = [
        r"cameras,\s+(\w+)\s+will handle",
        r"(\w+)\s+will handle the (?:mechanical|installation|install)",
    ]
    skip = {"we", "you", "they", "our", "i"}
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            name = match.group(1).strip()
            if name.lower() not in skip:
                return name if name[:1].isupper() else name.capitalize()
    return ""


def _parse_extra_news(text: str) -> str:
    match = re.search(
        r"extra news[^\n]*\n+(.+?)(?:\n\s*\n|What lies ahead|$)",
        text,
        re.I | re.S,
    )
    return match.group(1).strip() if match else ""


def _parse_roadmap(text: str) -> list[str]:
    section = ""
    match = re.search(r"What lies ahead of us:\s*\n(.+?)(?:\n\s*\nWould you|\Z)", text, re.I | re.S)
    if match:
        section = match.group(1)
    items: list[str] = []
    for line in section.splitlines():
        line = re.sub(r"^[\s⚙️📷📄📋🌾⚖️🇸🇰🤖📌\U0001f300-\U0001faff]+", "", line).strip()
        line = line.lstrip("-•* ").strip()
        if line:
            items.append(line)
    return items


def _extract_topics(text: str) -> str:
    lower = text.lower()
    found: list[str] = []
    for topic in _TOPIC_KEYWORDS:
        if topic.lower() in lower and topic not in found:
            found.append(topic)
    if not found:
        found = ["implementation", "pricing", "documentation"]
    return ", ".join(found)


def _build_notes(text: str, roadmap: list[str]) -> str:
    parts: list[str] = []
    if "laumas" in text.lower() or "m500" in text.lower():
        parts.append("Laumas M500 implementation discussed.")
    if "ucs-x3" in text.lower() and "diniargeo" in text.lower():
        parts.append("UCS-X3 on DiniArgeo planned.")
    if "camera" in text.lower():
        parts.append("Camera SW implementation; HW supplied by UCS, partner handles installation.")
    scale = re.search(r"(\d+)\s*scales?\s*per\s*year", text, re.I)
    if scale:
        parts.append(f"~{scale.group(1)} scales/year potential.")
    if "slovakia" in text.lower():
        parts.append("Slovakia market expansion discussed.")
    if roadmap:
        parts.append("Roadmap: " + "; ".join(roadmap[:4]))
    return " ".join(parts) if parts else text[:500]


def parse_followup_email(
    email_text: str,
    *,
    company: str = "",
    sales_rep_email: str = "",
    default_year: int = 2026,
) -> OpportunityNotePayload:
    text = _normalize(email_text)
    contact = _parse_greeting_contact(text)
    rep = _parse_sales_rep(text)
    meeting_date = _parse_meeting_date(text, default_year=default_year)
    parsed_company = company.strip() or _parse_company(text) or "Unknown Company"
    extra_news = _parse_extra_news(text)
    roadmap = _parse_roadmap(text)
    topics = _extract_topics(text)
    notes = _build_notes(text, roadmap)

    if not meeting_date:
        meeting_date = datetime.now().strftime("%Y-%m-%d")

    return OpportunityNotePayload(
        company=parsed_company,
        meeting_date=meeting_date,
        discussion_topics=topics,
        sales_rep=rep,
        sales_rep_email=sales_rep_email.strip(),
        contact_name=contact,
        extra_news=extra_news,
        notes=notes,
        event_type="followup_email_parsed",
    )


def is_followup_email(text: str) -> bool:
    text = _normalize(text)
    if not text:
        return False
    if text.startswith("{"):
        return False
    return bool(re.search(r"^Hi\s+[^,\n]+,", text, re.I | re.M)) or "What lies ahead of us" in text
