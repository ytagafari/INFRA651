"""CRM webhook payload schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def payload_from_request(data: dict[str, Any]) -> "OpportunityNotePayload":
    """Build payload from JSON dict, follow-up email, or UCS summary text."""
    from agent.email_parser import is_followup_email, parse_followup_email
    from agent.summary_parser import is_ucs_summary, parse_ucs_summary

    raw_text = str(
        data.get("input_summary", "")
        or data.get("input_email", "")
        or data.get("email_body", "")
    ).strip()

    if raw_text and is_ucs_summary(raw_text):
        return parse_ucs_summary(
            raw_text,
            sales_rep_email=str(data.get("sales_rep_email", "")).strip(),
            sales_rep_full_name=str(data.get("sales_rep_full_name", "")).strip(),
        )
    if raw_text and is_followup_email(raw_text):
        return parse_followup_email(
            raw_text,
            company=str(data.get("company", "")).strip(),
            sales_rep_email=str(data.get("sales_rep_email", "")).strip(),
        )
    payload = OpportunityNotePayload.from_dict(data)
    if not payload.input_mode:
        payload.input_mode = "crm_json"
    return payload


def payload_from_text(
    text: str,
    *,
    sales_rep_email: str = "",
    sales_rep_full_name: str = "",
) -> "OpportunityNotePayload":
    from agent.email_parser import is_followup_email, parse_followup_email
    from agent.summary_parser import is_ucs_summary, parse_ucs_summary

    text = text.strip()
    if is_ucs_summary(text):
        return parse_ucs_summary(
            text,
            sales_rep_email=sales_rep_email,
            sales_rep_full_name=sales_rep_full_name,
        )
    if is_followup_email(text):
        return parse_followup_email(text, sales_rep_email=sales_rep_email)
    return payload_from_request({"input_summary": text, "sales_rep_email": sales_rep_email})


@dataclass
class OpportunityNotePayload:
    company: str
    meeting_date: str
    discussion_topics: str
    opportunity_id: str = ""
    sales_rep: str = ""
    sales_rep_email: str = ""
    sales_rep_full_name: str = ""
    contact_name: str = ""
    extra_news: str = ""
    notes: str = ""
    input_mode: str = ""
    meeting_date_display: str = ""
    implementation_note: str = ""
    camera_note: str = ""
    delivery_note: str = ""
    required_summary: str = ""
    potential_note: str = ""
    required_items: str = ""
    scales_per_year: str = ""
    output_format: str = ""
    event_type: str = "opportunity_note_updated"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def validate(self) -> None:
        missing = [
            n
            for n, v in [
                ("company", self.company),
                ("meeting_date", self.meeting_date),
                ("discussion_topics", self.discussion_topics),
            ]
            if not str(v).strip()
        ]
        if missing:
            raise ValueError(f"Missing required CRM fields: {', '.join(missing)}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpportunityNotePayload":
        return cls(
            company=str(data.get("company", "")).strip(),
            meeting_date=str(data.get("meeting_date", "")).strip(),
            discussion_topics=str(data.get("discussion_topics", "")).strip(),
            opportunity_id=str(data.get("opportunity_id", "")).strip(),
            sales_rep=str(data.get("sales_rep", "")).strip(),
            sales_rep_email=str(data.get("sales_rep_email", "")).strip(),
            sales_rep_full_name=str(data.get("sales_rep_full_name", "")).strip(),
            contact_name=str(data.get("contact_name", "")).strip(),
            extra_news=str(data.get("extra_news", "")).strip(),
            notes=str(data.get("notes", "")).strip(),
            input_mode=str(data.get("input_mode", "")).strip(),
            meeting_date_display=str(data.get("meeting_date_display", "")).strip(),
            implementation_note=str(data.get("implementation_note", "")).strip(),
            camera_note=str(data.get("camera_note", "")).strip(),
            delivery_note=str(data.get("delivery_note", "")).strip(),
            required_summary=str(data.get("required_summary", "")).strip(),
            potential_note=str(data.get("potential_note", "")).strip(),
            required_items=str(data.get("required_items", "")).strip(),
            scales_per_year=str(data.get("scales_per_year", "")).strip(),
            output_format=str(data.get("output_format", "")).strip(),
            event_type=str(data.get("event_type", "opportunity_note_updated")).strip(),
        )
