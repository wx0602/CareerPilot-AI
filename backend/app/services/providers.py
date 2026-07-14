from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4


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
    """仅用于 B 独立联调，不实现 C 的真实解析或 RAG。"""

    def parse_material(self, path: Path, material_type: str) -> list[dict[str, Any]]:
        if path.suffix.lower() == ".txt":
            text = path.read_text(encoding="utf-8", errors="replace")[:5000]
        else:
            text = f"开发桩已接收 {material_type} 文件：{path.name}"
        return [
            {
                "chunk_id": str(uuid4()),
                "source_type": material_type,
                "text": text,
                "metadata": {"filename": path.name, "provider": "stub"},
            }
        ]


class StubAIProvider:
    """确定性开发桩，只验证 B 的编排、持久化和接口契约。"""

    _templates = [
        {
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
        {
            "question_type": "true_false",
            "content": "SQLite 是关系型数据库。",
            "options": [],
            "answer": "true",
            "explanation": "SQLite 是轻量级关系型数据库。",
            "knowledge_points": ["SQLite"],
        },
        {
            "question_type": "short_answer",
            "content": "请简述数据库索引的作用。",
            "options": [],
            "answer": "索引通过额外的数据结构提高查询效率，但会增加存储和写入成本。",
            "explanation": "应同时说明查询收益与维护成本。",
            "knowledge_points": ["数据库索引"],
        },
    ]

    def generate_exam(self, request: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        exam_id = str(uuid4())
        grading_items: list[dict[str, Any]] = []
        public_questions: list[dict[str, Any]] = []
        for index in range(request["question_count"]):
            template = dict(self._templates[index % len(self._templates)])
            question_id = f"stub-{index + 1}"
            full_item = {"question_id": question_id, **template}
            grading_items.append(full_item)
            public_questions.append(
                {
                    "question_id": question_id,
                    "question_type": template["question_type"],
                    "content": template["content"],
                    "options": template["options"],
                }
            )
        title_prefix = request.get("company") or "企业"
        paper = {
            "exam_id": exam_id,
            "session_id": request["session_id"],
            "title": f"{title_prefix} · {request['position']}笔试",
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
            "请介绍一个你参与过的后端项目，以及你承担的主要职责。",
            "你如何设计接口与数据库之间的事务边界？",
            "遇到线上接口性能问题时，你会如何定位？",
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
            "strengths": ["回答与问题相关"] if answer else [],
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
            suggestions = ["建议继续进行针对性练习并复盘回答。"]
        return {
            "session_id": request["session_id"],
            "mode": request["mode"],
            "overall_score": overall,
            "dimension_scores": {"专业知识": professional, "逻辑表达": communication},
            "strengths": ["完成了本次训练的核心环节"],
            "weaknesses": unique_weaknesses,
            "suggestions": suggestions,
            "charts": {"radar": {"专业知识": professional, "逻辑表达": communication}},
            "summary": "本报告由 B 的开发桩生成，仅用于验证接口与数据流程。",
        }


class UnavailableKnowledgeProvider:
    def parse_material(self, path: Path, material_type: str) -> list[dict[str, Any]]:
        raise ProviderUnavailableError("C 的材料解析函数尚未接入")


class UnavailableAIProvider:
    def _raise(self) -> None:
        raise ProviderUnavailableError("D 的 AI 函数尚未接入")

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


def build_providers(mode: str) -> tuple[KnowledgeProvider, AIProvider]:
    if mode == "stub":
        return StubKnowledgeProvider(), StubAIProvider()
    if mode == "real":
        return UnavailableKnowledgeProvider(), UnavailableAIProvider()
    raise ValueError("PROVIDER_MODE 只能是 stub 或 real")
