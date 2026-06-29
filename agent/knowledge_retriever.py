"""
Keyword + optional semantic vector retrieval over UCS knowledge base.
"""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from agent.drive_links import resolve_for_document

ROOT = Path(__file__).resolve().parents[1]
KB_ROOT = ROOT / "knowledge-base"
SHEETS = KB_ROOT / "sheets"


@dataclass
class Product:
    product_id: str
    product_name: str
    category: str
    description: str
    keywords: list[str]
    protocols: list[str]
    connectivity: list[str]
    mount_type: str
    cloud_service: str
    score: float = 0.0


@dataclass
class Document:
    doc_id: str
    title: str
    doc_type: str
    product_ids: list[str]
    keywords: list[str]
    drive_path: str
    local_path: str
    format: str
    drive_url: str = ""
    score: float = 0.0


@dataclass
class PriceEntry:
    product_id: str
    sku: str
    list_price_eur: str
    currency: str
    price_tier: str
    notes: str


@dataclass
class RetrievalResult:
    query_keywords: list[str]
    products: list[Product] = field(default_factory=list)
    documents: list[Document] = field(default_factory=list)
    prices: list[PriceEntry] = field(default_factory=list)
    retrieval_mode: str = "keyword"


_QUERY_ALIASES: dict[str, list[str]] = {
    "ucx3": ["ucs-x3", "x2", "x3", "gateway", "modbus", "iiot"],
    "ucs-x3": ["ucx3", "x2", "gateway", "modbus"],
    "pressage": ["weighing", "scale", "sensweight"],
    "silo": ["senssilo", "sensweight", "agriculture", "grain", "storage"],
}


def tokenize(text: str) -> list[str]:
    raw = re.split(r"[,;/|\n]+", text.lower())
    tokens: list[str] = []
    for part in raw:
        for word in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", part.strip()):
            if len(word) >= 2:
                tokens.append(word)
    expanded = list(tokens)
    for token in tokens:
        for alias in _QUERY_ALIASES.get(token, []):
            if alias not in expanded:
                expanded.append(alias)
    return list(dict.fromkeys(expanded))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _split_field(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _score_keywords(query: Iterable[str], haystack: Iterable[str]) -> float:
    query_set = set(query)
    haystack_set = set(haystack)
    if not query_set:
        return 0.0
    overlap = query_set & haystack_set
    if not overlap:
        partial = sum(1 for q in query_set for h in haystack_set if q in h or h in q)
        return partial * 0.5
    partial = sum(1 for q in query_set for h in haystack_set if q in h or h in q)
    return len(overlap) * 2.0 + partial * 0.5


def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    max_score = max(scores.values())
    if max_score <= 0:
        return scores
    return {key: value / max_score for key, value in scores.items()}


def _retrieval_settings() -> tuple[str, float, float]:
    mode = os.environ.get("RETRIEVAL_MODE", "hybrid").strip().lower()
    keyword_weight = float(os.environ.get("RETRIEVAL_KEYWORD_WEIGHT", "0.35"))
    vector_weight = float(os.environ.get("RETRIEVAL_VECTOR_WEIGHT", "0.65"))
    if mode not in {"hybrid", "keyword", "vector"}:
        mode = "hybrid"
    if mode == "keyword":
        keyword_weight, vector_weight = 1.0, 0.0
    elif mode == "vector":
        keyword_weight, vector_weight = 0.0, 1.0
    return mode, keyword_weight, vector_weight


class KnowledgeBase:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or KB_ROOT
        self.sheets_dir = self.base_dir / "sheets"
        self._products = self._load_products()
        self._documents = self._load_documents()
        self._prices = self._load_prices()
        self._vector_index = self._load_vector_index()

    def _load_vector_index(self):
        mode, _, _ = _retrieval_settings()
        if mode == "keyword":
            return None
        try:
            from agent.vector_store import VectorIndex

            return VectorIndex.load(self.base_dir)
        except Exception:
            return None

    @property
    def vector_index(self):
        return self._vector_index

    def _load_products(self) -> list[Product]:
        rows = _read_csv(self.sheets_dir / "Product-Catalog.csv")
        return [
            Product(
                product_id=row["product_id"],
                product_name=row["product_name"],
                category=row["category"],
                description=row["description"],
                keywords=_split_field(row["keywords"]),
                protocols=_split_field(row["protocols"]),
                connectivity=_split_field(row["connectivity"]),
                mount_type=row["mount_type"],
                cloud_service=row.get("cloud_service", "UCS CLOUD"),
            )
            for row in rows
        ]

    def _load_documents(self) -> list[Document]:
        rows = _read_csv(self.sheets_dir / "Document-Index.csv")
        documents: list[Document] = []
        for row in rows:
            local_path = row["local_path"]
            doc_id = row["doc_id"]
            documents.append(
                Document(
                    doc_id=doc_id,
                    title=row["title"],
                    doc_type=row["doc_type"],
                    product_ids=_split_field(row["product_ids"]),
                    keywords=_split_field(row["keywords"]),
                    drive_path=row["drive_path"],
                    local_path=local_path,
                    drive_url=resolve_for_document(doc_id, local_path),
                    format=row["format"],
                )
            )
        return documents

    def _load_prices(self) -> list[PriceEntry]:
        rows = _read_csv(self.sheets_dir / "Price-List.csv")
        return [
            PriceEntry(
                product_id=row["product_id"],
                sku=row["sku"],
                list_price_eur=row["list_price_eur"],
                currency=row["currency"],
                price_tier=row.get("price_tier", ""),
                notes=row.get("notes", ""),
            )
            for row in rows
        ]

    def retrieve(self, discussion_topics: str, notes: str = "", limit: int = 6) -> RetrievalResult:
        query_text = f"{discussion_topics} {notes}".strip()
        query_keywords = tokenize(query_text)
        mode, keyword_weight, vector_weight = _retrieval_settings()
        effective_mode = mode
        result = RetrievalResult(query_keywords=query_keywords, retrieval_mode=effective_mode)

        product_keyword_scores = {
            product.product_id: _score_keywords(
                query_keywords,
                product.keywords
                + tokenize(product.product_name)
                + tokenize(product.description)
                + tokenize(product.product_id),
            )
            for product in self._products
        }
        document_keyword_scores = {
            doc.doc_id: _score_keywords(
                query_keywords,
                doc.keywords + tokenize(doc.title) + tokenize(doc.doc_type),
            )
            for doc in self._documents
        }

        product_vector_scores: dict[str, float] = {}
        document_vector_scores: dict[str, float] = {}
        if self._vector_index and vector_weight > 0:
            try:
                product_vector_scores = self._vector_index.product_scores(query_text)
                document_vector_scores = self._vector_index.document_scores(query_text)
            except Exception:
                effective_mode = "keyword"
                keyword_weight, vector_weight = 1.0, 0.0
        elif mode in {"hybrid", "vector"}:
            effective_mode = "keyword"

        norm_product_keyword = _normalize_scores(product_keyword_scores)
        norm_document_keyword = _normalize_scores(document_keyword_scores)
        norm_product_vector = _normalize_scores(product_vector_scores)
        norm_document_vector = _normalize_scores(document_vector_scores)

        product_scores: dict[str, float] = {}
        for product in self._products:
            combined = (
                keyword_weight * norm_product_keyword.get(product.product_id, 0.0)
                + vector_weight * norm_product_vector.get(product.product_id, 0.0)
            )
            if combined > 0:
                product_scores[product.product_id] = combined

        document_scores: dict[str, float] = {}
        for doc in self._documents:
            combined = (
                keyword_weight * norm_document_keyword.get(doc.doc_id, 0.0)
                + vector_weight * norm_document_vector.get(doc.doc_id, 0.0)
            )
            if combined > 0:
                document_scores[doc.doc_id] = combined

        result.retrieval_mode = "hybrid" if keyword_weight and vector_weight else effective_mode

        scored_products: list[Product] = []
        for product in self._products:
            score = product_scores.get(product.product_id, 0.0)
            if score > 0:
                scored_products.append(Product(**{**product.__dict__, "score": score}))  # type: ignore[arg-type]
        result.products = sorted(scored_products, key=lambda p: p.score, reverse=True)[:limit]

        scored_docs: list[Document] = []
        for doc in self._documents:
            score = document_scores.get(doc.doc_id, 0.0)
            if score > 0:
                scored_docs.append(Document(**{**doc.__dict__, "score": score}))  # type: ignore[arg-type]
        result.documents = sorted(scored_docs, key=lambda d: d.score, reverse=True)[:limit]

        matched_ids = {p.product_id for p in result.products}
        for doc in result.documents:
            matched_ids.update(doc.product_ids)
        result.prices = [p for p in self._prices if p.product_id in matched_ids]

        if any(k in query_keywords for k in ("pricing", "price", "quote", "saas", "subscription", "cost")):
            for doc in self._documents:
                if doc.doc_type == "price_list" and doc not in result.documents:
                    result.documents.append(doc)

        return result

    def resolve_local_path(self, relative_path: str) -> Path:
        path = ROOT / relative_path
        return path if path.is_file() else path

    def document_exists(self, relative_path: str) -> bool:
        return self.resolve_local_path(relative_path).is_file()
