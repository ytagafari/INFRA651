"""UCS CRM agent orchestration."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from agent.email_attachments import build_attachments_from_documents
from agent.email_sender import maybe_send_to_sales_rep
from agent.email_formatter import (
    EMAIL_FORMAT_VERSION,
    build_email_html as build_ucs_html,
    build_email_plain as build_ucs_plain,
    build_email_subject as build_ucs_subject,
)
from agent.followup_formatter import (
    build_followup_html,
    build_followup_plain,
    build_followup_subject,
)
from agent.sales_response_formatter import (
    EMAIL_FORMAT_VERSION as SALES_FORMAT_VERSION,
    build_sales_response_html,
    build_sales_response_plain,
    build_sales_response_subject,
)
from agent.knowledge_retriever import KnowledgeBase, RetrievalResult
from agent.payload import OpportunityNotePayload

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


@dataclass
class AgentRunResult:
    payload: OpportunityNotePayload
    retrieval: RetrievalResult
    agent_prompt: str
    email_plain: str = ""
    email_html: str = ""
    email_subject: str = ""
    output_mode: str = ""
    email_sent: bool = False
    email_sent_to: str = ""
    email_send_error: str = ""
    email_attachment_count: int = 0
    email_attachment_names: list[str] | None = None
    output_path: str | None = None
    email_path: str | None = None
    email_html_path: str | None = None


def build_agent_prompt(payload: OpportunityNotePayload, retrieval: RetrievalResult) -> str:
    template = (PROMPTS_DIR / "sales-followup.md").read_text(encoding="utf-8")
    doc_lines = [
        f"- {d.title} ({d.doc_type}) score={d.score:.1f} | {d.drive_url or d.drive_path}"
        for d in retrieval.documents
    ]
    prod_lines = [f"- {p.product_name} [{p.product_id}] score={p.score:.1f}" for p in retrieval.products]
    price_lines = [f"- {pr.sku}: {pr.list_price_eur} {pr.currency} — {pr.notes}" for pr in retrieval.prices]
    return (
        template.replace("{{company}}", payload.company)
        .replace("{{meeting_date}}", payload.meeting_date)
        .replace("{{discussion_topics}}", payload.discussion_topics)
        .replace("{{notes}}", payload.notes or "(none)")
        .replace("{{sales_rep}}", payload.sales_rep or "(unknown)")
        .replace("{{keywords}}", ", ".join(retrieval.query_keywords))
        .replace("{{matched_products}}", "\n".join(prod_lines) or "- none")
        .replace("{{matched_documents}}", "\n".join(doc_lines) or "- none")
        .replace("{{matched_prices}}", "\n".join(price_lines) or "- none")
    )


class OpportunityAgent:
    def __init__(self) -> None:
        self.kb = KnowledgeBase()

    def handle(self, payload: OpportunityNotePayload) -> AgentRunResult:
        payload.validate()
        retrieval = self.kb.retrieve(payload.discussion_topics, payload.notes)
        prompt = build_agent_prompt(payload, retrieval)
        attachments, _attach_notes = build_attachments_from_documents(retrieval.documents)
        attached_names = [a.filename for a in attachments]

        if payload.input_mode == "ucs_summary":
            email_plain = build_followup_plain(payload, retrieval)
            email_html = build_followup_html(payload, retrieval)
            email_subject = build_followup_subject(payload)
            output_mode = "customer_followup"
            email_format = EMAIL_FORMAT_VERSION
        elif payload.output_format == "ucs_summary" or payload.input_mode == "ucs_internal":
            email_plain = build_ucs_plain(payload, retrieval)
            email_html = build_ucs_html(payload, retrieval)
            email_subject = build_ucs_subject(payload)
            output_mode = "ucs_summary"
            email_format = EMAIL_FORMAT_VERSION
        else:
            email_plain = build_sales_response_plain(payload, retrieval, attached_names)
            email_html = build_sales_response_html(payload, retrieval, attached_names)
            email_subject = build_sales_response_subject(payload, retrieval)
            output_mode = "sales_response"
            email_format = SALES_FORMAT_VERSION
        out_dir = ROOT / "agent" / "runs"
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = "".join(c.lower() if c.isalnum() else "-" for c in payload.company).strip("-")[:40]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = out_dir / f"{stamp}_{slug}.json"
        email_path = out_dir / f"{stamp}_{slug}.email.txt"
        email_html_path = out_dir / f"{stamp}_{slug}.email.html"
        artifact = {
            "payload": asdict(payload),
            "retrieval": {
                "query_keywords": retrieval.query_keywords,
                "products": [asdict(p) for p in retrieval.products],
                "documents": [asdict(d) for d in retrieval.documents],
                "prices": [asdict(p) for p in retrieval.prices],
            },
            "agent_prompt": prompt,
            "email_plain": email_plain,
            "email_html": email_html,
            "email_subject": email_subject,
            "output_mode": output_mode,
            "email_format": email_format,
            "email_attachments": [a.filename for a in attachments],
        }
        path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
        email_path.write_text(email_plain, encoding="utf-8-sig")
        email_html_path.write_text(email_html, encoding="utf-8-sig")
        send_result = maybe_send_to_sales_rep(
            payload,
            subject=email_subject,
            plain_body=email_plain,
            html_body=email_html,
            attachments=attachments,
        )
        return AgentRunResult(
            payload=payload,
            retrieval=retrieval,
            agent_prompt=prompt,
            email_plain=email_plain,
            email_html=email_html,
            email_subject=email_subject,
            output_mode=output_mode,
            email_sent=send_result.sent,
            email_sent_to=send_result.recipient,
            email_send_error=send_result.error,
            email_attachment_count=send_result.attachment_count,
            email_attachment_names=send_result.attachment_names or [],
            output_path=str(path),
            email_path=str(email_path),
            email_html_path=str(email_html_path),
        )
