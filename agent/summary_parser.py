"""Parse UCS AI meeting summary text into structured CRM payload."""

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


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def is_ucs_summary(text: str) -> bool:
    text = _normalize(text)
    if not text or text.startswith("{"):
        return False
    if text.startswith("Hi ") and "What lies ahead of us" in text:
        return False
    return "Summary" in text and ("Key Points" in text or "Meeting Date:" in text)


def _parse_date_long(text: str) -> tuple[str, str]:
    """Return (iso_date, display like June 9th)."""
    match = re.search(
        r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})",
        text,
    )
    if not match:
        return "", ""
    month_name, day_s, year_s = match.group(1).lower(), match.group(2), match.group(3)
    month = _MONTHS.get(month_name)
    if not month:
        return "", ""
    day = int(day_s)
    year = int(year_s)
    iso = f"{year:04d}-{month:02d}-{day:02d}"
    suffix = "th"
    if day % 10 == 1 and day != 11:
        suffix = "st"
    elif day % 10 == 2 and day != 12:
        suffix = "nd"
    elif day % 10 == 3 and day != 13:
        suffix = "rd"
    display = f"{month_name.capitalize()} {day}{suffix}"
    return iso, display


def _parse_attendees_line(text: str) -> tuple[str, str, str]:
    """Parse 'June 9, 2026 Bruto: Miloš, Colleague & Nikola'."""
    match = re.search(
        r"[A-Za-z]+\s+\d{1,2},?\s+\d{4}\s+([^:]+):\s*([^,&\n]+).*?&\s*([^\n]+)",
        text,
    )
    if match:
        return match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
    contact = ""
    m = re.search(r"between\s+([^,\n]+),\s+a colleague,\s+and\s+([^,\n.]+)", text, re.I)
    if m:
        contact, rep = m.group(1).strip(), m.group(2).strip()
        company = ""
        cm = re.search(r"(\w+)\s+team is ready", text, re.I)
        if cm:
            company = cm.group(1).strip()
        return company, contact, rep
    return "", "", ""


def _parse_key_point(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}:\s*(.+)", text, re.I)
    return match.group(1).strip() if match else ""


def _parse_required_items(text: str) -> list[str]:
    match = re.search(
        r"He needs the following information:\s*\n(.+?)(?:\n[A-Z][^\n]*potential|\Z)",
        text,
        re.I | re.S,
    )
    if not match:
        return []
    return [line.strip() for line in match.group(1).splitlines() if line.strip()]


def _parse_extra_news(text: str) -> str:
    match = re.search(
        r"(We have just ordered stickers.+?whole system\.?)",
        text,
        re.I | re.S,
    )
    return match.group(1).strip() if match else ""


def _parse_scale_line(text: str) -> str:
    match = re.search(r"(\d+)\s*scales?\s*per\s*year", text, re.I)
    return match.group(1) if match else ""


def parse_ucs_summary(
    summary_text: str,
    *,
    sales_rep_email: str = "",
    sales_rep_full_name: str = "",
) -> OpportunityNotePayload:
    text = _normalize(summary_text)
    iso_date, date_display = _parse_date_long(text)
    company, contact, rep = _parse_attendees_line(text)
    if not company:
        cm = re.search(r"The\s+(\w+)\s+team is ready", text, re.I)
        company = cm.group(1).strip() if cm else "Unknown Company"

    impl = _parse_key_point(text, "💻 Implementation") or _parse_key_point(text, "Implementation")
    camera = _parse_key_point(text, "📷 Camera System") or _parse_key_point(text, "Camera System")
    delivery = _parse_key_point(text, "🔧 Delivery") or _parse_key_point(text, "Delivery")
    required_label = _parse_key_point(text, "📄 Required Information") or _parse_key_point(
        text, "Required Information"
    )
    potential = _parse_key_point(text, "📈 Potential") or _parse_key_point(text, "Potential")
    required_items = _parse_required_items(text)
    extra_news = _parse_extra_news(text)
    scales = _parse_scale_line(text)

    topics_parts = []
    if "laumas" in text.lower():
        topics_parts.append("Laumas")
    if "ucs-x3" in text.lower() or "diniargeo" in text.lower():
        topics_parts.append("UCS-X3")
        topics_parts.append("DiniArgeo")
    if "camera" in text.lower():
        topics_parts.append("camera system")
    if "certificate" in text.lower():
        topics_parts.append("certificate")
    if "pricing" in text.lower() or "price list" in text.lower():
        topics_parts.append("pricing")
    if "marketing" in text.lower():
        topics_parts.append("marketing materials")
    if "slovakia" in text.lower():
        topics_parts.append("Slovakia")
    if "modbus" in text.lower():
        topics_parts.append("Modbus")

    full_rep = sales_rep_full_name.strip() or rep
    if full_rep == "Nikola":
        full_rep = "Nikola Avramović"

    return OpportunityNotePayload(
        company=company,
        meeting_date=iso_date or datetime.now().strftime("%Y-%m-%d"),
        discussion_topics=", ".join(topics_parts) or "implementation, pricing, documentation",
        sales_rep=rep or "Nikola",
        sales_rep_email=sales_rep_email.strip(),
        sales_rep_full_name=full_rep,
        contact_name=contact,
        extra_news=extra_news,
        notes=text[:2000],
        input_mode="ucs_summary",
        meeting_date_display=date_display,
        implementation_note=impl,
        camera_note=camera,
        delivery_note=delivery,
        required_summary=required_label,
        potential_note=potential,
        required_items="\n".join(required_items),
        scales_per_year=scales,
        event_type="ucs_summary_parsed",
    )
