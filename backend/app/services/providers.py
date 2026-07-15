from __future__ import annotations

import random
import shutil
import sys
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from ..core.config import IS_SERVERLESS, RUNTIME_DIR
from .learning_modules import default_question_mix, get_learning_module


class ProviderUnavailableError(RuntimeError):
    pass


class KnowledgeProvider(Protocol):
    def parse_material(self, path: Path, material_type: str) -> list[dict[str, Any]]: ...


class AIProvider(Protocol):
    def generate_exam(self, request: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]: ...

    def grade_exam(
        self,
        submission: dict[str, Any],
        grading_items: list[dict[str, Any]],
    ) -> dict[str, Any]: ...

    def generate_question(self, request: dict[str, Any]) -> dict[str, Any]: ...

    def evaluate_answer(self, request: dict[str, Any]) -> dict[str, Any]: ...

    def generate_report(self, request: dict[str, Any]) -> dict[str, Any]: ...


class StubKnowledgeProvider:
    """仅用于联调的材料解析占位实现。"""

    def parse_material(self, path: Path, material_type: str) -> list[dict[str, Any]]:
        if path.suffix.lower() == ".txt":
            text = path.read_text(encoding="utf-8", errors="replace")[:5000]
        else:
            text = f"已接收 {material_type} 文件: {path.name}"
        return [
            {
                "chunk_id": str(uuid4()),
                "source_type": material_type,
                "text": text,
                "metadata": {"filename": path.name, "provider": "stub"},
            }
        ]


class StubAIProvider:
    """确定性联调实现，验证会话、组卷和评分流程。"""

    _BASE_TEMPLATES = {
        "single_choice": {
            "question_type": "single_choice",
            "content": "HTTP 状态码 404 表示什么？",
            "options": [
                {"key": "A", "text": "请求成功"},
                {"key": "B", "text": "资源未找到"},
                {"key": "C", "text": "服务器内部错误"},
                {"key": "D", "text": "没有权限"},
            ],
            "answer": "B",
            "explanation": "404 表示服务器找不到请求的资源。",
            "knowledge_points": ["HTTP"],
        },
        "multiple_choice": {
            "question_type": "multiple_choice",
            "content": "下面哪些做法有助于提升接口稳定性？",
            "options": [
                {"key": "A", "text": "设置超时"},
                {"key": "B", "text": "增加重试保护"},
                {"key": "C", "text": "记录关键日志"},
                {"key": "D", "text": "忽略错误"},
            ],
            "answer": ["A", "B", "C"],
            "explanation": "超时、重试和日志都是稳定性治理的基础手段。",
            "knowledge_points": ["稳定性"],
        },
        "true_false": {
            "question_type": "true_false",
            "content": "SQLite 是关系型数据库。",
            "options": [],
            "answer": "true",
            "explanation": "SQLite 是轻量级关系型数据库。",
            "knowledge_points": ["SQLite"],
        },
        "short_answer": {
            "question_type": "short_answer",
            "content": "请简述数据库索引的作用。",
            "options": [],
            "answer": "索引通过额外的数据结构提升查询效率，但会增加存储和写入维护成本。",
            "explanation": "回答应同时说明查询收益与维护成本。",
            "knowledge_points": ["数据库索引"],
        },
    }

    def _build_stub_bank(self, request: dict[str, Any]) -> list[dict[str, Any]]:
        mix = request.get("question_mix") or {}
        if mix:
            counts = {
                "single_choice": int(mix.get("single_choice", 0)),
                "true_false": int(mix.get("true_false", 0)),
                "multiple_choice": int(mix.get("multiple_choice", 0)),
                "short_answer": int(mix.get("short_answer", 0)),
            }
        else:
            counts = {"single_choice": 0, "true_false": 0, "multiple_choice": 0, "short_answer": 0}
            for index in range(int(request.get("question_count", 10))):
                question_type = ("single_choice", "true_false", "short_answer")[index % 3]
                counts[question_type] += 1

        module_title = request.get("learning_module_title") or request.get("position") or "通用模块"
        bank: list[dict[str, Any]] = []
        ordinal = 1
        for question_type in ("single_choice", "true_false", "multiple_choice", "short_answer"):
            template = self._BASE_TEMPLATES[question_type]
            for number in range(counts[question_type]):
                content = f"[{module_title}] {template['content']}"
                bank.append(
                    {
                        "question_id": f"stub-{ordinal}",
                        "question_type": question_type,
                        "content": content,
                        "options": template["options"],
                        "answer": template["answer"],
                        "explanation": template["explanation"],
                        "knowledge_points": template["knowledge_points"],
                    }
                )
                ordinal += 1
        return bank

    def generate_exam(self, request: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        exam_id = str(uuid4())
        grading_items = self._build_stub_bank(request)
        public_questions = [
            {
                "question_id": item["question_id"],
                "question_type": item["question_type"],
                "content": item["content"],
                "options": item["options"],
            }
            for item in grading_items
        ]
        module_title = request.get("learning_module_title") or request.get("position") or "笔试练习"
        paper = {
            "exam_id": exam_id,
            "session_id": request["session_id"],
            "title": f"{module_title} 笔试练习",
            "questions": public_questions,
        }
        return paper, grading_items

    def grade_exam(
        self,
        submission: dict[str, Any],
        grading_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        answer_map = {item["question_id"]: item["answer"] for item in submission["answers"]}
        earned = 0
        results: list[dict[str, Any]] = []
        weak_points: list[str] = []
        for item in grading_items:
            user_answer = answer_map.get(item["question_id"], "")
            expected = item.get("answer")
            if item["question_type"] == "short_answer":
                item_score = 70 if len(str(user_answer).strip()) >= 10 else 0
                correct = item_score >= 60
            else:
                normalized_user = sorted(user_answer) if isinstance(user_answer, list) else str(user_answer).lower()
                normalized_expected = sorted(expected) if isinstance(expected, list) else str(expected).lower()
                correct = normalized_user == normalized_expected
                item_score = 100 if correct else 0
            earned += item_score
            if not correct:
                weak_points.extend(item.get("knowledge_points", []))
            results.append(
                {
                    "question_id": item["question_id"],
                    "correct": correct,
                    "user_answer": user_answer,
                    "correct_answer": expected,
                    "feedback": item.get("explanation", ""),
                }
            )
        score = round(earned / len(grading_items)) if grading_items else 0
        weaknesses = list(dict.fromkeys(weak_points))
        return {
            "exam_id": submission["exam_id"],
            "score": score,
            "question_results": results,
            "weaknesses": weaknesses,
            "suggestions": [f"建议复习：{point}" for point in weaknesses],
        }

    def generate_question(self, request: dict[str, Any]) -> dict[str, Any]:
        history_count = len(request.get("history", []))
        questions = [
            "请介绍一个你参与过的项目，以及你负责的核心工作。",
            "你会如何划分接口层和数据库事务边界？",
            "线上接口变慢时，你通常先看哪些观测指标？",
        ]
        return {
            "question_id": str(uuid4()),
            "question": questions[history_count % len(questions)],
        }

    def evaluate_answer(self, request: dict[str, Any]) -> dict[str, Any]:
        answer = request["answer"].strip()
        score = min(90, 45 + len(answer) // 2)
        need_followup = len(answer) < 30
        return {
            "question_id": request["question_id"],
            "score": score,
            "dimension_scores": {"专业知识": score, "逻辑表达": max(0, score - 5)},
            "strengths": ["回答切题"] if answer else [],
            "weaknesses": ["回答缺少具体细节"] if need_followup else [],
            "need_followup": need_followup,
            "followup_question": "请结合一个具体场景进一步说明。" if need_followup else None,
        }

    def generate_report(self, request: dict[str, Any]) -> dict[str, Any]:
        scores: list[int] = []
        weaknesses: list[str] = []
        suggestions: list[str] = []
        exam_result = request.get("exam_result")
        if exam_result:
            scores.append(exam_result["score"])
            weaknesses.extend(exam_result.get("weaknesses", []))
            suggestions.extend(exam_result.get("suggestions", []))
        evaluations = request.get("interview_evaluations", [])
        scores.extend(item["score"] for item in evaluations)
        for item in evaluations:
            weaknesses.extend(item.get("weaknesses", []))
        overall = round(sum(scores) / len(scores)) if scores else 0
        professional = exam_result["score"] if exam_result else overall
        communication = (
            round(sum(item["score"] for item in evaluations) / len(evaluations))
            if evaluations
            else overall
        )
        unique_weaknesses = list(dict.fromkeys(weaknesses))
        if not suggestions:
            suggestions = ["建议继续针对性练习并复盘作答。"]
        return {
            "session_id": request["session_id"],
            "mode": request["mode"],
            "overall_score": overall,
            "dimension_scores": {"专业知识": professional, "逻辑表达": communication},
            "strengths": ["完成了本次训练的核心环节"],
            "weaknesses": unique_weaknesses,
            "suggestions": suggestions,
            "charts": {"radar": {"专业知识": professional, "逻辑表达": communication}},
            "summary": "该报告由联调占位实现生成，用于验证接口和数据流。",
        }


class UnavailableKnowledgeProvider:
    def parse_material(self, path: Path, material_type: str) -> list[dict[str, Any]]:
        raise ProviderUnavailableError("材料解析 Provider 尚未接入。")


class UnavailableAIProvider:
    def _raise(self) -> None:
        raise ProviderUnavailableError("AI Provider 尚未接入。")

    def generate_exam(self, request: dict[str, Any]):
        self._raise()

    def grade_exam(self, submission: dict[str, Any], grading_items: list[dict[str, Any]]):
        self._raise()

    def generate_question(self, request: dict[str, Any]):
        self._raise()

    def evaluate_answer(self, request: dict[str, Any]):
        self._raise()

    def generate_report(self, request: dict[str, Any]):
        self._raise()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    cwd_path = (Path.cwd() / path).resolve()
    if cwd_path.exists():
        return cwd_path
    return (_project_root() / path).resolve()


def _ensure_import_paths() -> None:
    root = _project_root()
    for item in (root, root / "ai-core"):
        text = str(item)
        if text not in sys.path:
            sys.path.insert(0, text)


def _prepare_question_database(
    database_path: str | Path,
    *,
    serverless: bool = IS_SERVERLESS,
    runtime_dir: Path = RUNTIME_DIR,
) -> Path:
    source_path = _resolve_project_path(database_path)
    if serverless:
        try:
            source_path.relative_to(runtime_dir)
        except ValueError:
            pass
        else:
            source_path = _project_root() / "knowledge" / "question_bank" / source_path.name

    if not source_path.is_file():
        raise ProviderUnavailableError(f"题库源数据库不存在：{source_path}")
    if not serverless:
        return source_path

    target_path = runtime_dir / source_path.name
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not target_path.exists():
        shutil.copy2(source_path, target_path)
    return target_path


class RealKnowledgeProvider:
    """真实题库和材料解析入口。"""

    def __init__(
        self,
        *,
        database_path: str | Path = "knowledge/question_bank/questions.sqlite3",
        chroma_directory: str | Path | None = "knowledge/chroma_store",
        raw_question_dir: str | Path = "knowledge/question_bank/raw",
    ):
        _ensure_import_paths()
        from knowledge.rag import KnowledgeService

        self.database_path = _prepare_question_database(database_path)
        self.chroma_directory = _resolve_project_path(chroma_directory) if chroma_directory else None
        self.raw_question_dir = _resolve_project_path(raw_question_dir)
        self.service = KnowledgeService(
            database_path=self.database_path,
            chroma_directory=self.chroma_directory,
        )
        self._ensure_questions_loaded()

    def _ensure_questions_loaded(self) -> None:
        existing = self.service.search_questions("", top_k=1, include_answer=True)
        if existing.get("total", 0):
            return

        from knowledge.question_bank.validation import load_and_clean_questions

        imported = 0
        for source in sorted(self.raw_question_dir.glob("*.json")):
            questions, _rejected = load_and_clean_questions(source)
            if questions:
                result = self.service.import_questions(questions)
                imported += int(result.get("imported", 0))
        if imported == 0:
            raise ProviderUnavailableError("题库为空，无法使用真实题库生成笔试。")

    def parse_material(self, path: Path, material_type: str) -> list[dict[str, Any]]:
        from knowledge.models import ContextChunk
        from knowledge.parsers import parse_material

        material = parse_material(path, material_type=material_type, user_id="backend")
        self.service.index_material(material)
        context = ContextChunk(
            chunk_id=material.material_id,
            source_type=material.type,
            text=material.parsed_text[:5000],
            metadata={
                "filename": material.filename,
                "material_id": material.material_id,
                "structured_data": material.structured_data,
                "provider": "real",
            },
        )
        return [context.model_dump(mode="json")]


class RealAIProvider:
    """真实 AI Provider：调用 ai-core agent，并先按学习模块检索题库。"""

    def __init__(
        self,
        *,
        database_path: str | Path = "knowledge/question_bank/questions.sqlite3",
        chroma_directory: str | Path | None = "knowledge/chroma_store",
    ):
        _ensure_import_paths()
        from knowledge.rag import KnowledgeService

        self.knowledge = KnowledgeService(
            database_path=_prepare_question_database(database_path),
            chroma_directory=_resolve_project_path(chroma_directory) if chroma_directory else None,
        )

    @staticmethod
    def _question_target_count(request: dict[str, Any]) -> int:
        mix = request.get("question_mix")
        if mix:
            return sum(int(value) for value in mix.values())
        return int(request.get("question_count", default_question_mix().total()))

    @staticmethod
    def _deduplicate_questions(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        seen_contents: set[str] = set()
        for group in groups:
            for question in group:
                question_id = str(question["question_id"])
                normalized_content = " ".join(str(question["content"]).split()).casefold()
                if question_id in seen_ids or normalized_content in seen_contents:
                    continue
                seen_ids.add(question_id)
                seen_contents.add(normalized_content)
                selected.append(question)
        return selected

    @staticmethod
    def _shuffled(
        questions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        shuffled = questions[:]
        random.shuffle(shuffled)
        return shuffled

    def _select_questions(
        self,
        request: dict[str, Any],
        preferred: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        mix = request.get("question_mix")
        if not mix:
            count = self._question_target_count(request)
            preferred_ids = {item["question_id"] for item in preferred}
            fallback = [item for item in candidates if item["question_id"] not in preferred_ids]
            ordered = self._shuffled(preferred)
            ordered.extend(self._shuffled(fallback))
            if len(ordered) < count:
                raise ValueError(f"题库需要 {count} 道题，当前只有 {len(ordered)} 道")
            return ordered[:count]

        selected: list[dict[str, Any]] = []
        shortages: list[str] = []
        for question_type, raw_count in mix.items():
            count = int(raw_count)
            if count <= 0:
                continue
            preferred_bucket = [
                item for item in preferred if item["question_type"] == question_type
            ]
            preferred_ids = {item["question_id"] for item in preferred_bucket}
            fallback_bucket = [
                item
                for item in candidates
                if item["question_type"] == question_type
                and item["question_id"] not in preferred_ids
            ]
            ordered = self._shuffled(preferred_bucket)
            ordered.extend(
                self._shuffled(fallback_bucket)
            )
            if len(ordered) < count:
                shortages.append(f"{question_type} 需要 {count} 道，当前只有 {len(ordered)} 道")
                continue
            selected.extend(ordered[:count])

        if shortages:
            module_name = request.get("learning_module_title") or request.get("position") or "当前模块"
            raise ValueError(f"{module_name} 模块题库不足：{'; '.join(shortages)}")
        return selected

    def _search_question_bank(self, request: dict[str, Any]) -> list[dict[str, Any]]:
        module = get_learning_module(request.get("learning_module"))
        if module and not module.available:
            raise ValueError(f"{module.title} 模块题库暂未补充完成。")

        search_position = module.search_position if module else request.get("position")
        search_points = list(module.search_knowledge_points) if module and module.search_knowledge_points else None
        requested_count = self._question_target_count(request)
        top_k = max(requested_count * 8, 100)

        preferred_result = self.knowledge.search_questions(
            "",
            position=search_position,
            difficulty=request.get("difficulty"),
            knowledge_points=search_points,
            top_k=top_k,
            include_answer=True,
        )
        all_difficulties_result = self.knowledge.search_questions(
            "",
            position=search_position,
            knowledge_points=search_points,
            top_k=top_k,
            include_answer=True,
        )
        preferred = self._deduplicate_questions(preferred_result.get("questions", []))
        candidates = self._deduplicate_questions(
            preferred,
            all_difficulties_result.get("questions", []),
        )

        if not candidates and module:
            module_name = request.get("learning_module_title") or request.get("position") or "当前模块"
            raise ValueError(f"{module_name} 模块暂无可用题目，请先补充题库。")

        if not candidates:
            global_preferred = self.knowledge.search_questions(
                "",
                difficulty=request.get("difficulty"),
                top_k=top_k,
                include_answer=True,
            )
            global_fallback = self.knowledge.search_questions(
                "",
                top_k=top_k,
                include_answer=True,
            )
            preferred = self._deduplicate_questions(global_preferred.get("questions", []))
            candidates = self._deduplicate_questions(
                preferred,
                global_fallback.get("questions", []),
            )
        if not candidates:
            raise ProviderUnavailableError("题库检索结果为空，无法生成笔试。")
        return self._select_questions(request, preferred, candidates)

    def generate_exam(self, request: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        from agents import generate_exam

        question_bank = self._search_question_bank(request)
        paper = generate_exam(request, question_bank)
        bank_by_id = {item["question_id"]: item for item in question_bank}
        grading_items = [
            bank_by_id[question.question_id]
            for question in paper.questions
            if question.question_id in bank_by_id
        ]
        return paper.model_dump(mode="json"), grading_items

    def grade_exam(
        self,
        submission: dict[str, Any],
        grading_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        from agents import grade_exam

        expected_ids = [item["question_id"] for item in grading_items]
        result = grade_exam(submission, grading_items, expected_question_ids=expected_ids)
        return result.model_dump(mode="json")

    def generate_question(self, request: dict[str, Any]) -> dict[str, Any]:
        from agents import generate_question

        response = generate_question(request)
        return response.model_dump(mode="json")

    def evaluate_answer(self, request: dict[str, Any]) -> dict[str, Any]:
        from agents import evaluate_answer

        response = evaluate_answer(request)
        return response.model_dump(mode="json")

    def generate_report(self, request: dict[str, Any]) -> dict[str, Any]:
        from agents import generate_report

        response = generate_report(request)
        return response.model_dump(mode="json")


def build_providers(mode: str) -> tuple[KnowledgeProvider, AIProvider]:
    if mode == "stub":
        return StubKnowledgeProvider(), StubAIProvider()
    if mode == "real":
        return RealKnowledgeProvider(), RealAIProvider()
    raise ValueError("PROVIDER_MODE 只能是 stub 或 real")
