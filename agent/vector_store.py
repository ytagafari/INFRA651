"""Semantic vector index for UCS knowledge-base documents and products."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.knowledge_retriever import Document, Product

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
MANIFEST_NAME = "manifest.json"
DOCUMENTS_NAME = "documents.npz"
PRODUCTS_NAME = "products.npz"
_MODEL_CACHE: dict[str, object] = {}


def embeddings_dir(base_dir: Path | None = None) -> Path:
    root = base_dir or (ROOT / "knowledge-base")
    return Path(root) / "embeddings"


def document_embed_text(doc: Document) -> str:
    return (
        f"{doc.title}. Type: {doc.doc_type}. "
        f"Products: {', '.join(doc.product_ids)}. "
        f"Keywords: {', '.join(doc.keywords)}"
    )


def product_embed_text(product: Product) -> str:
    return (
        f"{product.product_name}. Category: {product.category}. "
        f"{product.description}. Keywords: {', '.join(product.keywords)}. "
        f"Protocols: {', '.join(product.protocols)}"
    )


@dataclass
class VectorIndex:
    model_name: str
    doc_ids: list[str]
    doc_embeddings: object
    product_ids: list[str]
    product_embeddings: object
    _model: object | None = None

    @classmethod
    def load(cls, base_dir: Path | None = None) -> VectorIndex | None:
        embed_dir = embeddings_dir(base_dir)
        manifest_path = embed_dir / MANIFEST_NAME
        docs_path = embed_dir / DOCUMENTS_NAME
        products_path = embed_dir / PRODUCTS_NAME
        if not manifest_path.is_file() or not docs_path.is_file() or not products_path.is_file():
            return None
        try:
            import numpy as np
        except ImportError:
            return None

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        doc_data = np.load(docs_path, allow_pickle=False)
        prod_data = np.load(products_path, allow_pickle=False)
        doc_ids = [str(item) for item in doc_data["ids"].tolist()]
        product_ids = [str(item) for item in prod_data["ids"].tolist()]
        return cls(
            model_name=str(manifest.get("model", DEFAULT_MODEL)),
            doc_ids=doc_ids,
            doc_embeddings=doc_data["embeddings"],
            product_ids=product_ids,
            product_embeddings=prod_data["embeddings"],
        )

    def _ensure_model(self) -> object:
        if self._model is None:
            if self.model_name not in _MODEL_CACHE:
                from sentence_transformers import SentenceTransformer

                _MODEL_CACHE[self.model_name] = SentenceTransformer(self.model_name)
            self._model = _MODEL_CACHE[self.model_name]
        return self._model

    def _encode_query(self, query: str) -> object:
        import numpy as np

        model = self._ensure_model()
        vector = model.encode(query, normalize_embeddings=True)
        return np.asarray(vector, dtype=np.float32)

    @staticmethod
    def _score_ids(ids: list[str], matrix: object, query_vector: object) -> dict[str, float]:
        import numpy as np

        if len(ids) == 0:
            return {}
        scores = np.asarray(matrix, dtype=np.float32) @ np.asarray(query_vector, dtype=np.float32)
        return {doc_id: float(score) for doc_id, score in zip(ids, scores.tolist())}

    def document_scores(self, query: str) -> dict[str, float]:
        query_vector = self._encode_query(query)
        return self._score_ids(self.doc_ids, self.doc_embeddings, query_vector)

    def product_scores(self, query: str) -> dict[str, float]:
        query_vector = self._encode_query(query)
        return self._score_ids(self.product_ids, self.product_embeddings, query_vector)


def build_vector_index(
    documents: list[Document],
    products: list[Product],
    *,
    base_dir: Path | None = None,
    model_name: str = DEFAULT_MODEL,
) -> VectorIndex:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    doc_ids = [doc.doc_id for doc in documents]
    product_ids = [product.product_id for product in products]
    doc_texts = [document_embed_text(doc) for doc in documents]
    product_texts = [product_embed_text(product) for product in products]

    doc_embeddings = np.asarray(
        model.encode(doc_texts, normalize_embeddings=True, show_progress_bar=False),
        dtype=np.float32,
    )
    product_embeddings = np.asarray(
        model.encode(product_texts, normalize_embeddings=True, show_progress_bar=False),
        dtype=np.float32,
    )

    embed_dir = embeddings_dir(base_dir)
    embed_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "model": model_name,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(doc_ids),
        "product_count": len(product_ids),
        "dimensions": int(doc_embeddings.shape[1]) if len(doc_embeddings) else 0,
    }
    (embed_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    np.savez_compressed(embed_dir / DOCUMENTS_NAME, ids=np.array(doc_ids), embeddings=doc_embeddings)
    np.savez_compressed(embed_dir / PRODUCTS_NAME, ids=np.array(product_ids), embeddings=product_embeddings)

    return VectorIndex(
        model_name=model_name,
        doc_ids=doc_ids,
        doc_embeddings=doc_embeddings,
        product_ids=product_ids,
        product_embeddings=product_embeddings,
        _model=model,
    )
