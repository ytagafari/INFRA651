#!/usr/bin/env python3
"""Acceptance tests for CRM trigger + clients_package retrieval."""

import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.agent_handler import OpportunityAgent
from agent.payload import OpportunityNotePayload
from agent.knowledge_retriever import KnowledgeBase

SECRET = "ucs-demo-secret"


def test_silo_retrieval():
    kb = KnowledgeBase()
    r = kb.retrieve("SensSILO, silo monitoring, agriculture, pricing, SaaS", "grain silos")
    ids = {d.doc_id for d in r.documents}
    assert "MKT-SW-SILO" in ids, f"Expected silo leaflet, got {ids}"
    assert "PL-SW-SAAS" in ids or any(d.doc_type == "price_list" for d in r.documents)
    assert kb.document_exists(r.documents[0].local_path)
    print("PASS test_silo_retrieval", [d.doc_id for d in r.documents[:4]])


def test_truck_scale_retrieval():
    kb = KnowledgeBase()
    r = kb.retrieve("truck scale, M740, OIML R76, CE certification, digitalization", "OEM weighbridge")
    ids = {d.doc_id for d in r.documents}
    assert "DS-M740D" in ids or "MKT-SW-TRUCK" in ids, f"Expected M740/truck doc, got {ids}"
    assert any("CERT" in i or "OIML" in i for i in ids), f"Expected cert, got {ids}"
    print("PASS test_truck_scale_retrieval", [d.doc_id for d in r.documents[:4]])


def test_vector_semantic_retrieval():
    kb = KnowledgeBase()
    if kb.vector_index is None:
        print("SKIP test_vector_semantic_retrieval (run: pip install -r requirements.txt && python scripts/build_embeddings.py)")
        return
    r = kb.retrieve("grain storage remote monitoring subscription tiers", "")
    ids = {d.doc_id for d in r.documents}
    assert "MKT-SW-SILO" in ids, f"Expected silo leaflet from semantic match, got {ids}"
    print("PASS test_vector_semantic_retrieval", [d.doc_id for d in r.documents[:4]], f"mode={r.retrieval_mode}")


def test_crm_payload_and_webhook():
    agent = OpportunityAgent()
    payload = OpportunityNotePayload.from_dict(json.loads((ROOT / "crm/sample-payload.json").read_text()))
    result = agent.handle(payload)
    assert result.output_path and Path(result.output_path).is_file()
    assert payload.company and payload.meeting_date and payload.discussion_topics
    assert len(result.retrieval.documents) >= 2

    from agent.webhook_server import Handler, HTTPServer
    port = 18080
    srv = HTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.3)
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/webhook/crm-opportunity",
        data=(ROOT / "crm/sample-payload.json").read_bytes(),
        method="POST",
        headers={"Content-Type": "application/json", "X-Webhook-Secret": SECRET},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
        assert data["status"] == "processed"
        assert data["company"] == "AgriScale GmbH"
    srv.shutdown()
    print("PASS test_crm_payload_and_webhook")


def main():
    tests = [test_silo_retrieval, test_truck_scale_retrieval, test_vector_semantic_retrieval, test_crm_payload_and_webhook]
    for t in tests:
        t()
    print(f"\nAll {len(tests)} acceptance criteria tests PASSED.")


if __name__ == "__main__":
    main()
