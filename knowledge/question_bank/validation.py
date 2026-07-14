from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from knowledge.models import DIFFICULTIES, QUESTION_TYPES, QuestionOption, StoredQuestion


class QuestionValidationError(ValueError):
    pass


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _validate_options(raw_options: Any) -> list[QuestionOption]:
    if raw_options is None:
        return []
    if not isinstance(raw_options, list):
        raise QuestionValidationError("options 必须是数组")
    options: list[QuestionOption] = []
    try:
        for raw in raw_options:
            if not isinstance(raw, dict):
                raise QuestionValidationError("每个选项必须包含 key 和 text")
            option = QuestionOption(
                key=_clean_text(raw.get("key")).upper(),
                text=_clean_text(raw.get("text")),
            )
            if not option.key or not option.text:
                raise QuestionValidationError("选项 key 和 text 不能为空")
            options.append(option)
    except ValidationError as exc:
        raise QuestionValidationError(str(exc)) from exc
    keys = [option.key for option in options]
    if len(keys) != len(set(keys)):
        raise QuestionValidationError("选项 key 不能重复")
    return options


def validate_question(raw: dict[str, Any]) -> StoredQuestion:
    required = {
        "question_id",
        "company",
        "position",
        "difficulty",
        "question_type",
        "content",
        "options",
        "answer",
        "knowledge_points",
        "explanation",
    }
    missing = sorted(key for key in required if key not in raw)
    if missing:
        raise QuestionValidationError(f"缺少字段: {', '.join(missing)}")

    question_type = _clean_text(raw["question_type"]).lower()
    difficulty = _clean_text(raw["difficulty"]).lower()
    if question_type not in QUESTION_TYPES:
        raise QuestionValidationError(f"不支持的题型: {question_type}")
    if difficulty not in DIFFICULTIES:
        raise QuestionValidationError(f"不支持的难度: {difficulty}")

    options = _validate_options(raw.get("options"))
    option_keys = {option.key for option in options}
    answer: str | list[str] | None = raw.get("answer")

    if question_type in {"single_choice", "multiple_choice"} and len(options) < 2:
        raise QuestionValidationError("选择题至少需要两个选项")
    if question_type == "single_choice":
        answer = _clean_text(answer).upper()
        if answer not in option_keys:
            raise QuestionValidationError("单选题答案必须对应一个选项 key")
    elif question_type == "multiple_choice":
        if not isinstance(answer, list):
            raise QuestionValidationError("多选题答案必须是选项 key 数组")
        answer = list(dict.fromkeys(_clean_text(item).upper() for item in answer))
        if not answer or not set(answer).issubset(option_keys):
            raise QuestionValidationError("多选题答案包含不存在的选项 key")
    elif question_type == "true_false":
        aliases = {"true": "true", "false": "false", "正确": "true", "错误": "false"}
        normalized = _clean_text(answer).lower()
        if normalized not in aliases:
            raise QuestionValidationError("判断题答案必须是 true/false 或 正确/错误")
        answer = aliases[normalized]
        if options:
            raise QuestionValidationError("判断题 options 应为空数组")
    else:
        answer = _clean_text(answer)
        if not answer:
            raise QuestionValidationError("简答题参考答案不能为空")

    raw_points = raw.get("knowledge_points")
    if not isinstance(raw_points, list):
        raise QuestionValidationError("knowledge_points 必须是数组")
    points = list(dict.fromkeys(_clean_text(item) for item in raw_points if _clean_text(item)))
    if not points:
        raise QuestionValidationError("knowledge_points 不能为空")

    text_fields = {
        name: _clean_text(raw[name])
        for name in ("question_id", "company", "position", "content")
    }
    empty = [name for name, value in text_fields.items() if not value]
    if empty:
        raise QuestionValidationError(f"字段不能为空: {', '.join(empty)}")

    question = StoredQuestion(
        **text_fields,
        difficulty=difficulty,
        question_type=question_type,
        options=options,
        answer=answer,
        knowledge_points=points,
        explanation=_clean_text(raw.get("explanation")) or None,
        source=_clean_text(raw.get("source")) or "原创整理",
        source_url=_clean_text(raw.get("source_url")),
        license=_clean_text(raw.get("license")) or "original",
    )
    # 最终公共字段必须通过根目录 QuestionBankItem 的 Pydantic 校验。
    question.to_bank_item()
    return question


def clean_questions(
    items: Iterable[dict[str, Any]],
) -> tuple[list[StoredQuestion], list[dict[str, Any]]]:
    cleaned: list[StoredQuestion] = []
    rejected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_contents: set[str] = set()
    for index, raw in enumerate(items):
        try:
            question = validate_question(raw)
            content_key = question.content.casefold()
            if question.question_id in seen_ids:
                raise QuestionValidationError(f"重复题号: {question.question_id}")
            if content_key in seen_contents:
                raise QuestionValidationError("题干重复")
            seen_ids.add(question.question_id)
            seen_contents.add(content_key)
            cleaned.append(question)
        except (QuestionValidationError, ValidationError, TypeError, KeyError) as exc:
            rejected.append(
                {
                    "index": index,
                    "question_id": raw.get("question_id", ""),
                    "reason": str(exc),
                }
            )
    return cleaned, rejected


def load_and_clean_questions(
    path: str | Path,
) -> tuple[list[StoredQuestion], list[dict[str, Any]]]:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise QuestionValidationError("题库根节点必须是 JSON 数组")
    return clean_questions(payload)


def save_questions(questions: Iterable[StoredQuestion], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump([item.to_dict() for item in questions], handle, ensure_ascii=False, indent=2)
