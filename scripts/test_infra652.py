#!/usr/bin/env python3
"""Acceptance tests for INFRA-652: credibility, document selection, client profile."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.agent_handler import OpportunityAgent
from agent.client_profile import PROFILES_DIR, load_profile
from agent.credibility_assessor import assess_credibility
from agent.document_selector import select_documents
from agent.knowledge_retriever import KnowledgeBase
from agent.payload import OpportunityNotePayload


def test_credibility_summary():
    result = assess_credibility(
        "AgriScale GmbH",
        "SensSILO, silo monitoring, agriculture, pricing, SaaS",
        "38 grain silos Bavaria",
    )
    assert result.credibility_score >= 60, result.summary
    assert result.industry == "agriculture"
    assert "agriculture" in result.summary.lower() or "AgriScale" in result.summary
    assert result.credibility_level in {"medium-high", "high"}
    print("PASS test_credibility_summary", result.credibility_score, result.credibility_level)


def test_document_selection():
    kb = KnowledgeBase()
    retrieval = kb.retrieve(
        "truck scale, M740, OIML R76, CE certification, pricing",
        "OEM weighbridge",
    )
    selection = select_documents(retrieval, "truck scale, M740, OIML R76, CE certification, pricing", "OEM")
    ids = {d.doc_id for d in selection.documents}
    types = set(selection.by_type.keys())
    assert "MKT-SW-TRUCK" in ids or "DS-M740D" in ids or "DS-M740-60T" in ids, ids
    assert "certification" in types or any("CERT" in i for i in ids), types
    print("PASS test_document_selection", list(ids)[:5], selection.by_type)


def test_client_profile_saved():
    if PROFILES_DIR.exists():
        for old in PROFILES_DIR.glob("agriscale-gmbh.json"):
            old.unlink()
    agent = OpportunityAgent()
    payload = OpportunityNotePayload.from_dict(json.loads((ROOT / "crm/sample-payload.json").read_text()))
    result = agent.handle(payload)
    assert result.credibility and result.credibility.credibility_score > 0
    assert result.selected_documents and len(result.selected_documents.documents) >= 2
    assert result.client_profile and result.profile_path
    assert Path(result.profile_path).is_file()
    loaded = load_profile("agriscale-gmbh")
    assert loaded and loaded.meeting_count >= 1
    assert "MKT-SW-SILO" in loaded.documents_sent or loaded.documents_sent
    print("PASS test_client_profile_saved", result.profile_path)


def main():
    tests = [test_credibility_summary, test_document_selection, test_client_profile_saved]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} INFRA-652 acceptance tests PASSED.")


if __name__ == "__main__":
    main()
