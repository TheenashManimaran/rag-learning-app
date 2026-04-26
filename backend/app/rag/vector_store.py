import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from app.core.config import settings
from app.core.gemini import gemini


class VectorStore:
    def _base_path(self, user_id: str, document_id: str) -> Path:
        safe = f"u_{user_id}_d_{document_id}".replace("-", "_")
        path = settings.chroma_dir / safe
        path.mkdir(parents=True, exist_ok=True)
        return path

    def add_chunks(self, user_id: str, document_id: str, chunks: list[dict[str, Any]]) -> None:
        base_path = self._base_path(user_id, document_id)
        texts = [str(chunk["text"]) for chunk in chunks]
        embeddings = np.array(gemini.embed(texts, task_type="RETRIEVAL_DOCUMENT"), dtype="float32")
        faiss.normalize_L2(embeddings)
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        faiss.write_index(index, str(base_path / "index.faiss"))
        metadata = [
            {
                "document_id": document_id,
                "user_id": user_id,
                "page": int(chunk["page"]),
                "text": text,
            }
            for chunk, text in zip(chunks, texts)
        ]
        (base_path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    def retrieve(self, user_id: str, document_id: str, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        base_path = self._base_path(user_id, document_id)
        index_path = base_path / "index.faiss"
        metadata_path = base_path / "metadata.json"
        if not index_path.exists() or not metadata_path.exists():
            return []

        index = faiss.read_index(str(index_path))
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        query_embedding = np.array(gemini.embed([query], task_type="RETRIEVAL_QUERY"), dtype="float32")
        faiss.normalize_L2(query_embedding)
        scores, indices = index.search(query_embedding, min(top_k or settings.top_k, len(metadata)))
        chunks = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            item = metadata[int(idx)]
            chunks.append({"text": item["text"], "page": item["page"], "score": float(score)})
        return chunks


vector_store = VectorStore()
