from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from models import ContextChunk, Difficulty, QuestionBankItem, QuestionOption, QuestionType


QUESTION_TYPES = {"single_choice", "multiple_choice", "true_false", "short_answer"}
DIFFICULTIES = {"easy", "medium", "hard"}
MATERIAL_TYPES = {"resume", "jd", "project_intro", "business_plan", "pitch_ppt"}
MATERIAL_TYPE_ALIASES = {"pitch_deck": "pitch_ppt"}


@dataclass(slots=True)
class StoredQuestion:
    """C 的内部题库记录。

    公共题目字段严格对应根目录 QuestionBankItem；企业、岗位、难度和
    来源字段仅用于 C 的过滤、检索与溯源。
    """

    question_id: str
    company: str
    position: str
    difficulty: Difficulty
    question_type: QuestionType
    content: str
    answer: str | list[str] | None
    knowledge_points: list[str]
    explanation: str | None = None
    options: list[QuestionOption] = field(default_factory=list)
    source: str = "原创整理"
    source_url: str = ""
    license: str = "original"

    def to_bank_item(self, *, include_answer: bool = True) -> QuestionBankItem:
        return QuestionBankItem(
            question_id=self.question_id,
            question_type=self.question_type,
            content=self.content,
            options=self.options,
            answer=self.answer if include_answer else None,
            explanation=self.explanation if include_answer else None,
            knowledge_points=self.knowledge_points,
        )

    def to_dict(self) -> dict[str, Any]:
        data = self.to_bank_item().model_dump(mode="json")
        data.update(
            {
                "company": self.company,
                "position": self.position,
                "difficulty": self.difficulty,
                "source": self.source,
                "source_url": self.source_url,
                "license": self.license,
            }
        )
        return data


@dataclass(slots=True)
class ParsedMaterial:
    material_id: str
    user_id: str
    type: str
    filename: str
    parsed_text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    structured_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["metadata"].setdefault("created_at", datetime.now(timezone.utc).isoformat())
        return data

    def to_context(
        self,
        *,
        chunk_id: str | None = None,
        text: str | None = None,
        **metadata: Any,
    ) -> ContextChunk:
        context_metadata = {
            "material_id": self.material_id,
            "user_id": self.user_id,
            "filename": self.filename,
            **self.metadata,
            **metadata,
        }
        return ContextChunk(
            chunk_id=chunk_id or self.material_id,
            source_type=self.type,
            text=text or self.parsed_text,
            metadata=context_metadata,
        )


__all__ = [
    "ContextChunk",
    "Difficulty",
    "QuestionBankItem",
    "QuestionOption",
    "QuestionType",
    "StoredQuestion",
    "ParsedMaterial",
]
