#!/usr/bin/env python3
"""Build semantic vector embeddings for the UCS knowledge base."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.knowledge_retriever import KnowledgeBase
from agent.vector_store import DEFAULT_MODEL, build_vector_index, embeddings_dir


def main() -> int:
    kb = KnowledgeBase()
    print(f"Building embeddings with model: {DEFAULT_MODEL}")
    index = build_vector_index(kb._documents, kb._products, base_dir=kb.base_dir, model_name=DEFAULT_MODEL)
    out = embeddings_dir(kb.base_dir)
    print(f"Saved {len(index.doc_ids)} document vectors and {len(index.product_ids)} product vectors")
    print(f"Output: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
