#!/usr/bin/env python3
"""Webhook: CRM opportunity note -> UCS agent + clients_package doc retrieval."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

from agent.agent_handler import OpportunityAgent
from agent.email_formatter import EMAIL_FORMAT_VERSION
from agent.email_sender import load_dotenv
from agent.payload import OpportunityNotePayload, payload_from_request
from agent.text_encoding import repair_text


def decode_request_body(raw: bytes, content_type: str = "") -> str:
    """Decode POST body as UTF-8 (preferred). Fall back only if UTF-8 fails."""
    if not raw:
        return ""
    charset = content_type.lower()
    if "charset=utf-8" in charset or "charset=utf8" in charset:
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        for encoding in ("cp1250", "cp1252", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
    return raw.decode("utf-8", errors="replace")


SECRET = os.environ.get("CRM_WEBHOOK_SECRET", "ucs-demo-secret")
HOST = os.environ.get("WEBHOOK_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", os.environ.get("WEBHOOK_PORT", "8080")))


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, body: dict[str, Any]) -> None:
        data = json.dumps(body, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            self._json(200, {"status": "ok", "email_format": EMAIL_FORMAT_VERSION})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/webhook/crm-opportunity":
            return self._json(404, {"error": "not found"})
        if self.headers.get("X-Webhook-Secret") != SECRET:
            return self._json(401, {"error": "unauthorized"})
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        try:
            text = decode_request_body(raw, self.headers.get("Content-Type", ""))
            data = json.loads(text)
            for key, value in list(data.items()):
                if isinstance(value, str):
                    data[key] = repair_text(value)
            payload = payload_from_request(data)
            result = OpportunityAgent().handle(payload)
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
            hint = ""
            if isinstance(e, UnicodeDecodeError):
                hint = " Use: Get-Content file.json -Raw -Encoding UTF8"
            return self._json(400, {"error": str(e) + hint})
        self._json(200, {
            "status": "processed",
            "email_format": EMAIL_FORMAT_VERSION,
            "company": payload.company,
            "meeting_date": payload.meeting_date,
            "keywords": result.retrieval.query_keywords,
            "matched_documents": [
                {
                    "doc_id": d.doc_id,
                    "title": d.title,
                    "drive_path": d.drive_path,
                    "drive_url": d.drive_url,
                    "score": d.score,
                }
                for d in result.retrieval.documents
            ],
            "matched_products": [p.product_id for p in result.retrieval.products],
            "artifact_path": result.output_path,
            "email_path": result.email_path,
            "email_html_path": result.email_html_path,
            "email_subject": result.email_subject,
            "output_mode": result.output_mode,
            "email": result.email_plain,
            "email_html": result.email_html,
            "email_attachments": result.email_attachment_names or [],
            "email_attachment_count": result.email_attachment_count,
            "email_sent": result.email_sent,
            "email_sent_to": result.email_sent_to,
            "email_send_error": result.email_send_error or None,
        })

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[webhook] {self.address_string()} - {format % args}")


def main() -> None:
    load_dotenv()
    print(f"Webhook http://{HOST}:{PORT}/webhook/crm-opportunity")
    print(f"Email format: {EMAIL_FORMAT_VERSION} (restart server after code changes)")
    HTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
