from __future__ import annotations

import random
import uuid
from typing import Any, Sequence

from pydantic import BaseModel, Field

from agents.llm_client import call_json_model, read_prompt, to_jsonable
from agents.model_imports import REPO_ROOT  # noqa: F401
from models import (
    ExamPaperResponse,
    ExamQuestion,
    ExamResultResponse,
    ExamSubmission,
    GenerateExamRequest,
    QuestionBankItem,
)
from scoring.objective import grade_objective_question, is_objective
from scoring.summary import average_score, build_suggestions, collect_weaknesses
from skills.definitions import get_skill, skill_to_payload


class ShortAnswerGrade(BaseModel):
    question_id: str
    score: int = Field(ge=0, le=100)
    correct: bool
    feedback: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


def _validate_question_bank(
    question_bank: Sequence[QuestionBankItem | dict[str, Any]],
) -> list[QuestionBankItem]:
    return [
        item if isinstance(item, QuestionBankItem) else QuestionBankItem.model_validate(item)
        for item in question_bank
    ]


class ExamAgent:
    """负责组卷、客观题批改、简答题评分和错题分析。"""

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        task_type = state["task_type"]
        if task_type == "generate_exam":
            response = self.generate_exam(state["request"], state.get("question_bank", []))
        elif task_type == "grade_exam":
            response = self.grade_exam(
                state["request"],
                state.get("question_bank", []),
                state.get("expected_question_ids"),
            )
        else:
            raise ValueError(f"ExamAgent 不支持任务: {task_type}")
        return {"response": response}

    def generate_exam(
        self,
        request: GenerateExamRequest | dict[str, Any],
        question_bank: Sequence[QuestionBankItem | dict[str, Any]],
    ) -> ExamPaperResponse:
        req = request if isinstance(request, GenerateExamRequest) else GenerateExamRequest.model_validate(request)
        bank = _validate_question_bank(question_bank)
        if not bank:
            raise ValueError("题库为空，无法生成试卷。")

        seed = (
            f"{req.session_id}:{req.learning_module or ''}:{req.position}:"
            f"{req.company or ''}:{req.difficulty}"
        )
        if req.question_mix is None:
            selected = bank[:]
            random.Random(seed).shuffle(selected)
            selected = selected[: req.question_count]
        else:
            selected = []
            shortages: list[str] = []
            for question_type, count in req.question_mix.model_dump().items():
                bucket = [item for item in bank if item.question_type == question_type]
                random.Random(f"{seed}:{question_type}").shuffle(bucket)
                if len(bucket) < count:
                    shortages.append(f"{question_type} 需要 {count} 道，当前只有 {len(bucket)} 道")
                    continue
                selected.extend(bucket[:count])
            if shortages:
                module_name = req.learning_module_title or req.position
                raise ValueError(f"{module_name} 模块题库不足：{'; '.join(shortages)}")
            random.Random(f"{seed}:final").shuffle(selected)

        questions = [
            ExamQuestion(
                question_id=item.question_id,
                question_type=item.question_type,
                content=item.content,
                options=item.options,
            )
            for item in selected
        ]
        return ExamPaperResponse(
            exam_id=f"exam_{uuid.uuid4().hex[:12]}",
            session_id=req.session_id,
            title=f"{req.learning_module_title or req.position} 笔试练习（{req.difficulty}）",
            questions=questions,
        )

    def grade_exam(
        self,
        submission: ExamSubmission | dict[str, Any],
        question_bank: Sequence[QuestionBankItem | dict[str, Any]],
        expected_question_ids: Sequence[str] | None = None,
    ) -> ExamResultResponse:
        sub = submission if isinstance(submission, ExamSubmission) else ExamSubmission.model_validate(submission)
        bank = {item.question_id: item for item in _validate_question_bank(question_bank)}
        answers = {item.question_id: item for item in sub.answers}
        results: list[dict[str, Any]] = []

        for question_id, submitted in answers.items():
            question = bank.get(question_id)
            if question is None:
                results.append(
                    {
                        "question_id": question_id,
                        "correct": False,
                        "score": 0,
                        "user_answer": submitted.answer,
                        "feedback": "题库中未找到该题，无法批改。",
                        "knowledge_points": [],
                    }
                )
                continue

            if is_objective(question):
                results.append(grade_objective_question(question, submitted))
                continue

            skill = get_skill("short_answer_grading")
            grade = call_json_model(
                system_prompt=read_prompt(skill.prompt_file),
                user_payload={
                    "skill": skill_to_payload(skill),
                    "question": to_jsonable(question),
                    "submitted_answer": to_jsonable(submitted),
                    "target_schema": ShortAnswerGrade.model_json_schema(),
                },
                response_model=ShortAnswerGrade,
            )
            grade_result = grade.model_dump(mode="json")
            grade_result["question_type"] = question.question_type
            grade_result["user_answer"] = submitted.answer
            grade_result["correct_answer"] = question.answer
            grade_result["knowledge_points"] = question.knowledge_points
            results.append(grade_result)

        unanswered_ids = (
            [] if expected_question_ids is None else [qid for qid in expected_question_ids if qid not in answers]
        )
        for question_id in unanswered_ids:
            question = bank[question_id]
            results.append(
                {
                    "question_id": question_id,
                    "question_type": question.question_type,
                    "correct": False,
                    "score": 0,
                    "user_answer": "",
                    "correct_answer": question.answer,
                    "feedback": "未作答。",
                    "knowledge_points": question.knowledge_points,
                }
            )

        weaknesses = collect_weaknesses(results)
        return ExamResultResponse(
            exam_id=sub.exam_id,
            score=average_score(results),
            question_results=results,
            weaknesses=weaknesses,
            suggestions=build_suggestions(weaknesses),
        )


def generate_exam(
    request: GenerateExamRequest | dict[str, Any],
    question_bank: Sequence[QuestionBankItem | dict[str, Any]],
) -> ExamPaperResponse:
    from agents.workflow import run_workflow

    return run_workflow(
        {
            "task_type": "generate_exam",
            "request": request,
            "question_bank": question_bank,
        }
    )


def grade_exam(
    submission: ExamSubmission | dict[str, Any],
    question_bank: Sequence[QuestionBankItem | dict[str, Any]],
    expected_question_ids: Sequence[str] | None = None,
) -> ExamResultResponse:
    from agents.workflow import run_workflow

    return run_workflow(
        {
            "task_type": "grade_exam",
            "request": submission,
            "question_bank": question_bank,
            "expected_question_ids": expected_question_ids,
        }
    )
