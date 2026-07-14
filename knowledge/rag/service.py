from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from knowledge.models import ContextChunk, ParsedMaterial, QuestionBankItem, StoredQuestion
from knowledge.question_bank.repository import QuestionRepository
from knowledge.rag.chroma_index import ChromaIndex, ChromaUnavailableError
from knowledge.rag.vectorizer import lexical_score


class KnowledgeService:
    """B 和 D 调用的 C 模块统一入口。"""

    def __init__(
        self,
        *,
        database_path: str | Path,
        chroma_directory: str | Path | None = None,
        material_store_path: str | Path | None = None,
    ):
        self.questions = QuestionRepository(database_path)
        self.chroma_directory = Path(chroma_directory) if chroma_directory else None
        self.material_store_path = Path(
            material_store_path or Path(database_path).with_name("materials.jsonl")
        )
        self.material_store_path.parent.mkdir(parents=True, exist_ok=True)

    def import_questions(self, questions: Iterable[StoredQuestion]) -> dict[str, Any]:
        rows = list(questions)
        imported = self.questions.upsert_many(rows)
        indexed = 0
        backend = "sqlite"
        index = self._get_index("careerpilot_questions_v2")
        if index:
            indexed = index.upsert(
                {
                    "id": q.question_id,
                    "document": self._question_document(q),
                    "metadata": {
                        "company": q.company,
                        "position": q.position,
                        "difficulty": q.difficulty,
                        "question_type": q.question_type,
                        "knowledge_points": q.knowledge_points,
                    },
                }
                for q in rows
            )
            backend = "sqlite+chroma"
        return {"imported": imported, "indexed": indexed, "backend": backend}

    def search_questions(
        self,
        query: str = "",
        *,
        position: str | None = None,
        company: str | None = None,
        difficulty: str | None = None,
        question_type: str | None = None,
        knowledge_points: list[str] | None = None,
        top_k: int = 10,
        include_answer: bool = True,
    ) -> dict[str, Any]:
        """检索题库，同时返回公共 QuestionBankItem 和 ContextChunk。

        questions 用于 D 组卷；contexts 用于 D 的 RAG 上下文。
        """

        top_k = max(1, min(top_k, 100))
        candidates = self.questions.list_questions(
            position=position,
            company=company,
            difficulty=difficulty,
            question_type=question_type,
        )
        requested_points = {point.casefold() for point in (knowledge_points or [])}
        if requested_points:
            candidates = [
                item
                for item in candidates
                if requested_points & {point.casefold() for point in item.knowledge_points}
            ]

        backend = "sqlite-keyword"
        scored: list[tuple[float, StoredQuestion]] = []
        index = self._get_index("careerpilot_questions_v2") if query else None
        if index:
            where = {
                key: value
                for key, value in {
                    "position": position,
                    "company": company,
                    "difficulty": difficulty,
                    "question_type": question_type,
                }.items()
                if value
            }
            vector_hits = index.query(query, top_k=max(top_k * 5, 50), where=where or None)
            candidate_map = {item.question_id: item for item in candidates}
            scored = [
                (float(hit["score"]), candidate_map[hit["id"]])
                for hit in vector_hits
                if hit["id"] in candidate_map
            ]
            backend = "chroma"
        if not scored:
            if index:
                backend = "sqlite-keyword-fallback"
            for item in candidates:
                score = lexical_score(query, self._question_document(item)) if query else 1.0
                scored.append((score, item))

        scored.sort(key=lambda pair: (-pair[0], pair[1].question_id))
        if query and any(score > 0 for score, _ in scored):
            scored = [pair for pair in scored if pair[0] > 0]
        selected = scored[:top_k]

        question_models: list[QuestionBankItem] = [
            question.to_bank_item(include_answer=include_answer) for _, question in selected
        ]
        contexts: list[ContextChunk] = []
        for score, question in selected:
            public_question = question.to_bank_item(include_answer=include_answer)
            contexts.append(
                ContextChunk(
                    chunk_id=question.question_id,
                    source_type="question_bank",
                    text=question.content,
                    metadata={
                        "score": round(score, 6),
                        "company": question.company,
                        "position": question.position,
                        "difficulty": question.difficulty,
                        "source": question.source,
                        "source_url": question.source_url,
                        "question": public_question.model_dump(mode="json"),
                    },
                )
            )

        filters = {
            "position": position,
            "company": company,
            "difficulty": difficulty,
            "question_type": question_type,
            "knowledge_points": knowledge_points or [],
        }
        return {
            "query": query,
            "questions": [item.model_dump(mode="json") for item in question_models],
            "contexts": [item.model_dump(mode="json") for item in contexts],
            "total": len(selected),
            "backend": backend,
            "filters": filters,
        }

    def index_material(
        self,
        material: ParsedMaterial,
        *,
        chunk_size: int = 500,
        overlap: int = 80,
    ) -> dict[str, Any]:
        record = material.to_dict()
        with self.material_store_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        chunks = split_text(material.parsed_text, chunk_size=chunk_size, overlap=overlap)
        index = self._get_index("careerpilot_materials_v2")
        indexed = 0
        if index:
            indexed = index.upsert(
                {
                    "id": f"{material.material_id}:{number}",
                    "document": chunk,
                    "metadata": {
                        "material_id": material.material_id,
                        "user_id": material.user_id,
                        "source_type": material.type,
                        "filename": material.filename,
                        "chunk_index": number,
                    },
                }
                for number, chunk in enumerate(chunks)
            )
        return {
            "material_id": material.material_id,
            "chunks": len(chunks),
            "indexed": indexed,
            "backend": "chroma" if index else "jsonl-keyword",
        }

    def search_materials(
        self,
        query: str,
        *,
        user_id: str | None = None,
        material_type: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """返回严格符合根目录 ContextChunk 的材料召回结果。"""

        top_k = max(1, min(top_k, 50))
        where = {
            key: value
            for key, value in {
                "user_id": user_id,
                "source_type": material_type,
            }.items()
            if value
        }
        index = self._get_index("careerpilot_materials_v2")
        if index:
            hits = index.query(query, top_k=top_k, where=where or None)
            backend = "chroma"
        else:
            hits = self._search_materials_locally(query, user_id, material_type, top_k)
            backend = "jsonl-keyword"

        contexts = [
            ContextChunk(
                chunk_id=hit["id"],
                source_type=hit["metadata"]["source_type"],
                text=hit["content"],
                metadata={
                    **hit["metadata"],
                    "score": round(float(hit["score"]), 6),
                },
            )
            for hit in hits
        ]
        return {
            "query": query,
            "contexts": [item.model_dump(mode="json") for item in contexts],
            "total": len(contexts),
            "backend": backend,
            "filters": where,
        }

    def _search_materials_locally(
        self,
        query: str,
        user_id: str | None,
        material_type: str | None,
        top_k: int,
    ) -> list[dict[str, Any]]:
        if not self.material_store_path.exists():
            return []
        best_by_id: dict[str, dict[str, Any]] = {}
        with self.material_store_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                if user_id and record["user_id"] != user_id:
                    continue
                if material_type and record["type"] != material_type:
                    continue
                score = lexical_score(query, record["parsed_text"])
                candidate = {
                    "id": record["material_id"],
                    "score": score,
                    "content": record["parsed_text"][:1000],
                    "metadata": {
                        "material_id": record["material_id"],
                        "user_id": record["user_id"],
                        "source_type": record["type"],
                        "filename": record["filename"],
                        "structured_data": record.get("structured_data", {}),
                    },
                }
                if score > best_by_id.get(record["material_id"], {}).get("score", -1):
                    best_by_id[record["material_id"]] = candidate
        return sorted(best_by_id.values(), key=lambda item: -item["score"])[:top_k]

    def _get_index(self, name: str) -> ChromaIndex | None:
        if not self.chroma_directory:
            return None
        try:
            return ChromaIndex(self.chroma_directory, name)
        except ChromaUnavailableError:
            return None

    @staticmethod
    def _question_document(question: StoredQuestion) -> str:
        return " ".join(
            [
                question.content,
                question.explanation or "",
                question.position,
                question.company,
                *question.knowledge_points,
            ]
        )


def split_text(text: str, *, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须满足 0 <= overlap < chunk_size")
    paragraphs = [paragraph.strip() for paragraph in text.split("\n") if paragraph.strip()]
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 1 <= chunk_size:
            buffer = f"{buffer}\n{paragraph}".strip()
            continue
        if buffer:
            chunks.append(buffer)
            buffer = buffer[-overlap:] + "\n" + paragraph
        else:
            start = 0
            while start < len(paragraph):
                chunks.append(paragraph[start : start + chunk_size])
                start += chunk_size - overlap
            buffer = ""
    if buffer:
        chunks.append(buffer)
    return chunks or ([text[:chunk_size]] if text else [])
