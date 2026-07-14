from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from knowledge.rag.vectorizer import hashed_embedding


class ChromaUnavailableError(RuntimeError):
    pass


class ChromaIndex:
    """Persistent Chroma wrapper using deterministic offline embeddings."""

    def __init__(self, persist_directory: str | Path, collection_name: str):
        try:
            import chromadb
        except ImportError as exc:
            raise ChromaUnavailableError("未安装 chromadb，将使用 SQLite 本地检索") from exc
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(persist_directory))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, records: Iterable[dict[str, Any]]) -> int:
        rows = list(records)
        if not rows:
            return 0
        documents = [str(row["document"]) for row in rows]
        self.collection.upsert(
            ids=[str(row["id"]) for row in rows],
            documents=documents,
            metadatas=[_flat_metadata(row.get("metadata", {})) for row in rows],
            embeddings=[hashed_embedding(document) for document in documents],
        )
        return len(rows)

    def query(
        self,
        text: str,
        *,
        top_k: int = 10,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {
            "query_embeddings": [hashed_embedding(text)],
            "n_results": max(1, top_k),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            conditions = [{key: value} for key, value in where.items()]
            kwargs["where"] = conditions[0] if len(conditions) == 1 else {"$and": conditions}
        result = self.collection.query(**kwargs)
        return [
            {
                "id": item_id,
                "content": document,
                "metadata": metadata or {},
                "score": round(max(0.0, 1.0 - float(distance)), 6),
            }
            for item_id, document, metadata, distance in zip(
                result["ids"][0],
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
            )
        ]


def _flat_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    result: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            result[key] = value
        elif value is not None:
            result[key] = ",".join(map(str, value)) if isinstance(value, list) else str(value)
    return result
