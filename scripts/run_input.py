#!/usr/bin/env python3
"""Run agent from JSON, follow-up email (.txt), or UCS summary (.txt)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.agent_handler import OpportunityAgent
from agent.email_formatter import EMAIL_FORMAT_VERSION
from agent.email_sender import load_dotenv
from agent.payload import OpportunityNotePayload, payload_from_text


def load_input(path: Path, rep_email: str, rep_name: str) -> OpportunityNotePayload:
    text = path.read_text(encoding="utf-8-sig").strip()
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if rep_email:
            data["sales_rep_email"] = rep_email
        if rep_name:
            data["sales_rep_full_name"] = rep_name
        from agent.payload import payload_from_request
        return payload_from_request(data)
    return payload_from_text(text, sales_rep_email=rep_email, sales_rep_full_name=rep_name)


def print_result(result, payload: OpportunityNotePayload) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("Input mode:", payload.input_mode or payload.event_type)
    print("Output mode:", result.output_mode)
    print("Company:", payload.company)
    print("Contact:", payload.contact_name or "(none)")
    print("Sales rep:", payload.sales_rep_full_name or payload.sales_rep or "(none)")
    print("Meeting date:", payload.meeting_date)
    print("Subject:", result.email_subject)
    print("Output file:", result.email_path)
    if result.email_sent:
        print("Email sent to:", result.email_sent_to)
        if result.email_attachment_count:
            print("Attachments:", result.email_attachment_count, result.email_attachment_names)
    elif result.email_send_error:
        print("Email NOT sent:", result.email_send_error)
    print()
    label = {
        "customer_followup": "CUSTOMER FOLLOW-UP EMAIL",
        "sales_response": "SALES RESPONSE EMAIL (send to customer)",
        "ucs_summary": "UCS SUMMARY (internal)",
    }.get(result.output_mode, result.output_mode.upper())
    print(f"--- {label} ---")
    print(result.email_plain)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run UCS agent from JSON or text input")
    parser.add_argument(
        "input_file",
        nargs="?",
        default=str(ROOT / "crm" / "bruto-ucs-input.txt"),
        help="Path to .txt (UCS summary or follow-up email) or .json",
    )
    parser.add_argument("--rep-email", default="yt.agafari@unifiedcloudsensors.com")
    parser.add_argument("--rep-name", default="Nikola Avramović")
    parser.add_argument("--output", choices=("sales", "summary"), default="sales",
                        help="sales=customer email with docs/pricing (default for JSON); summary=internal UCS note")
    args = parser.parse_args()

    path = Path(args.input_file)
    if not path.is_file():
        print(f"ERROR: File not found: {path}")
        return 1

    load_dotenv()
    payload = load_input(path, args.rep_email, args.rep_name)
    if path.suffix.lower() == ".json" and args.output == "summary":
        payload.output_format = "ucs_summary"
    result = OpportunityAgent().handle(payload)
    print_result(result, payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
