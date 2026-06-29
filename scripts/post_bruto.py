#!/usr/bin/env python3
"""Run Bruto test payload through the agent (always uses latest code)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.agent_handler import OpportunityAgent
from agent.email_formatter import EMAIL_FORMAT_VERSION
from agent.email_sender import load_dotenv
from agent.payload import OpportunityNotePayload

SECRET = "ucs-demo-secret"
URL = "http://127.0.0.1:8080/webhook/crm-opportunity"


def run_direct(payload_path: Path) -> dict:
    load_dotenv()
    payload = OpportunityNotePayload.from_dict(
        json.loads(payload_path.read_text(encoding="utf-8"))
    )
    result = OpportunityAgent().handle(payload)
    return {
        "status": "processed",
        "email_format": EMAIL_FORMAT_VERSION,
        "company": payload.company,
        "email_subject": result.email_subject,
        "email_path": result.email_path,
        "email_sent": result.email_sent,
        "email_sent_to": result.email_sent_to,
        "email_send_error": result.email_send_error or None,
        "email": result.email_plain,
    }


def run_webhook(payload_path: Path) -> dict:
    body = payload_path.read_bytes()
    req = urllib.request.Request(
        URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Webhook-Secret": SECRET,
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def print_result(data: dict) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("Status:", data.get("status"))
    print("Format:", data.get("email_format"))
    print("Company:", data.get("company"))
    print("Subject:", data.get("email_subject"))
    print("Email file:", data.get("email_path"))

    if data.get("email_format") and data.get("email_format") != EMAIL_FORMAT_VERSION:
        print()
        print("WARNING: Webhook is running OLD code. Restart it:")
        print("  Ctrl+C in webhook terminal, then: python -m agent.webhook_server")

    if data.get("email", "").startswith("Hi "):
        print()
        print("WARNING: Old Nikola email format detected. Restart webhook or run without --webhook")

    if data.get("email_sent"):
        print("Email sent to:", data.get("email_sent_to"))
    elif data.get("email_send_error"):
        print("Email NOT sent:", data.get("email_send_error"))

    print()
    print("--- EMAIL PREVIEW ---")
    print(data.get("email", ""))


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Bruto CRM payload")
    parser.add_argument(
        "--webhook",
        action="store_true",
        help="Send via HTTP webhook instead of running agent directly",
    )
    args = parser.parse_args()

    payload_path = ROOT / "crm" / "bruto-meeting.json"

    try:
        if args.webhook:
            data = run_webhook(payload_path)
        else:
            data = run_direct(payload_path)
    except urllib.error.URLError as exc:
        print("ERROR: Could not reach webhook. Start it first:")
        print("  python -m agent.webhook_server")
        print("Or run without --webhook to use latest code directly.")
        print(exc)
        return 1

    print_result(data)
    return 0 if data.get("status") == "processed" else 1


if __name__ == "__main__":
    sys.exit(main())
