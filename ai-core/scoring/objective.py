from __future__ import annotations

from typing import Any

from agents.model_imports import REPO_ROOT  # noqa: F401
from models import QuestionBankItem, SubmittedAnswer


OBJECTIVE_TYPES = {"single_choice", "multiple_choice", "true_false"}


def normalize_answer(answer: str | list[str] | None) -> str | tuple[str, ...] | None:
    # 统一大小写和多选题选项顺序，保证客观题批改稳定。
    if answer is None:
        return None
    if isinstance(answer, list):
        return tuple(sorted(str(item).strip().upper() for item in answer))
    value = str(answer).strip()
    if value.lower() in {"true", "false"}:
        return value.lower()
    return value.upper()


def grade_objective_question(
    question: QuestionBankItem,
    submitted: SubmittedAnswer | None,
) -> dict[str, Any]:
    # 客观题批改是确定性逻辑，不消耗大模型 token。
    user_answer = submitted.answer if submitted else ""
    correct = normalize_answer(user_answer) == normalize_answer(question.answer)
    return {
        "question_id": question.question_id,
        "question_type": question.question_type,
        "correct": correct,
        "score": 100 if correct else 0,
        "user_answer": user_answer,
        "correct_answer": question.answer,
        "feedback": "回答正确。" if correct else (question.explanation or "回答错误，请复习相关知识点。"),
        "knowledge_points": question.knowledge_points,
    }


def is_objective(question: QuestionBankItem) -> bool:
    return question.question_type in OBJECTIVE_TYPES
