"""Send follow-up emails to the sales rep (Google Apps Script Web App or SMTP)."""

from __future__ import annotations

import base64
import json
import os
import re
import smtplib
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from agent.email_attachments import EmailAttachment, attachments_for_webapp
from agent.payload import OpportunityNotePayload

ROOT = Path(__file__).resolve().parents[1]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class EmailSendResult:
    sent: bool
    recipient: str = ""
    error: str = ""
    method: str = ""
    attachment_count: int = 0
    attachment_names: list[str] | None = None


def resolve_recipient(payload: OpportunityNotePayload) -> str:
    return payload.sales_rep_email.strip()


def send_enabled() -> bool:
    load_dotenv()
    return os.environ.get("SEND_EMAIL", "").strip().lower() in ("1", "true", "yes")


def webapp_configured() -> bool:
    load_dotenv()
    return bool(
        os.environ.get("GMAIL_WEBAPP_URL", "").strip()
        and os.environ.get("GMAIL_WEBAPP_SECRET", "").strip()
    )


def smtp_configured() -> bool:
    load_dotenv()
    return bool(
        os.environ.get("SMTP_USER", "").strip()
        and os.environ.get("SMTP_PASSWORD", "").strip()
    )


def send_via_gmail_webapp(
    *,
    recipient: str,
    subject: str,
    plain_body: str,
    html_body: str = "",
    attachments: list[EmailAttachment] | None = None,
) -> EmailSendResult:
    load_dotenv()
    url = os.environ.get("GMAIL_WEBAPP_URL", "").strip()
    secret = os.environ.get("GMAIL_WEBAPP_SECRET", "").strip()
    payload_data: dict[str, object] = {
        "secret": secret,
        "to": recipient,
        "subject": subject,
        "body": plain_body,
    }
    if html_body.strip():
        payload_data["html"] = html_body
    if attachments:
        payload_data["attachments"] = attachments_for_webapp(attachments)
    payload = json.dumps(payload_data, ensure_ascii=False).encode("utf-8")
    names = [a.filename for a in attachments or []]
    timeout = 120 if attachments else 30
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("sent"):
            return EmailSendResult(
                sent=True,
                recipient=recipient,
                method="gmail_webapp",
                attachment_count=len(attachments or []),
                attachment_names=names,
            )
        return EmailSendResult(
            sent=False,
            recipient=recipient,
            method="gmail_webapp",
            error=data.get("error", "Gmail Web App send failed"),
        )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return EmailSendResult(
            sent=False,
            recipient=recipient,
            method="gmail_webapp",
            error=f"Gmail Web App HTTP {exc.code}: {body}",
        )
    except urllib.error.URLError as exc:
        return EmailSendResult(
            sent=False,
            recipient=recipient,
            method="gmail_webapp",
            error=f"Could not reach GMAIL_WEBAPP_URL: {exc.reason}",
        )


def send_via_smtp(
    *,
    recipient: str,
    subject: str,
    plain_body: str,
    html_body: str = "",
    attachments: list[EmailAttachment] | None = None,
) -> EmailSendResult:
    load_dotenv()
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    sender = os.environ.get("SMTP_FROM", user).strip()

    if attachments:
        msg: MIMEMultipart = MIMEMultipart("mixed")
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(plain_body, "plain", "utf-8"))
        if html_body.strip():
            alt.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt)
        for item in attachments:
            part = MIMEApplication(base64.b64decode(item.content_base64), _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename=item.filename)
            msg.attach(part)
    else:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        if html_body.strip():
            msg.attach(MIMEText(html_body, "html", "utf-8"))

    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    names = [a.filename for a in attachments or []]

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=context)
            server.login(user, password)
            server.sendmail(sender, [recipient], msg.as_string())
        return EmailSendResult(
            sent=True,
            recipient=recipient,
            method="smtp",
            attachment_count=len(attachments or []),
            attachment_names=names,
        )
    except smtplib.SMTPAuthenticationError as exc:
        detail = str(exc)
        if "Application-specific password required" in detail or "534" in detail:
            detail = (
                "Gmail SMTP needs an App Password. Easier fix: deploy crm/apps-script/Email-Sender.gs "
                "as a Web App and set GMAIL_WEBAPP_URL in .env (no App Password needed). "
                "Or create one at https://myaccount.google.com/apppasswords"
            )
        return EmailSendResult(sent=False, recipient=recipient, method="smtp", error=detail)
    except (OSError, smtplib.SMTPException) as exc:
        return EmailSendResult(sent=False, recipient=recipient, method="smtp", error=str(exc))


def send_followup_email(
    *,
    recipient: str,
    subject: str,
    plain_body: str,
    html_body: str = "",
    attachments: list[EmailAttachment] | None = None,
) -> EmailSendResult:
    load_dotenv()
    if not recipient:
        return EmailSendResult(
            sent=False,
            error="Missing sales_rep_email in CRM row (add the rep's email address)",
        )
    if not EMAIL_RE.match(recipient):
        return EmailSendResult(sent=False, recipient=recipient, error=f"Invalid email address: {recipient}")
    if not send_enabled():
        return EmailSendResult(
            sent=False,
            recipient=recipient,
            error="Email sending disabled (set SEND_EMAIL=1 in .env)",
        )

    if webapp_configured():
        result = send_via_gmail_webapp(
            recipient=recipient,
            subject=subject,
            plain_body=plain_body,
            html_body=html_body,
            attachments=attachments,
        )
        if result.sent:
            return result
        if not smtp_configured():
            return result

    if smtp_configured():
        return send_via_smtp(
            recipient=recipient,
            subject=subject,
            plain_body=plain_body,
            html_body=html_body,
            attachments=attachments,
        )

    return EmailSendResult(
        sent=False,
        recipient=recipient,
        error=(
            "No email transport configured. Deploy crm/apps-script/Email-Sender.gs and set "
            "GMAIL_WEBAPP_URL + GMAIL_WEBAPP_SECRET in .env, or set SMTP_USER + SMTP_PASSWORD."
        ),
    )


def maybe_send_to_sales_rep(
    payload: OpportunityNotePayload,
    *,
    subject: str,
    plain_body: str,
    html_body: str = "",
    attachments: list[EmailAttachment] | None = None,
) -> EmailSendResult:
    recipient = resolve_recipient(payload)
    if not recipient:
        rep = payload.sales_rep or "sales rep"
        return EmailSendResult(
            sent=False,
            error=f"Missing sales_rep_email for {rep} - add their email in the CRM row",
        )
    return send_followup_email(
        recipient=recipient,
        subject=subject,
        plain_body=plain_body,
        html_body=html_body,
        attachments=attachments,
    )
