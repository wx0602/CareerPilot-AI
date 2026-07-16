from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator


InterviewMode = Literal["job", "technical", "pitch", "group_interview", "stress_interview"]
SimulationMode = Literal["group_interview", "stress_interview"]
StressLevel = Literal["light", "medium", "high"]
SimulationStage = Literal[
    "case_intro",
    "individual_statement",
    "free_discussion",
    "disagreement_resolution",
    "consensus",
    "summary",
    "opening",
    "probing",
    "paused",
    "closing",
    "scoring",
]
Difficulty = Literal["easy", "medium", "hard"]
QuestionType = Literal["single_choice", "multiple_choice", "true_false", "short_answer"]
Score = Annotated[int, Field(ge=0, le=100)]


class QuestionMix(BaseModel):
    single_choice: int = Field(default=5, ge=0, le=50)
    true_false: int = Field(default=5, ge=0, le=50)
    multiple_choice: int = Field(default=2, ge=0, le=50)
    short_answer: int = Field(default=3, ge=0, le=50)

    def total(self) -> int:
        return self.single_choice + self.true_false + self.multiple_choice + self.short_answer


class UserInfo(BaseModel):
    user_id: str | None = None
    account: str | None = None
    is_guest: bool


class LoginRequest(BaseModel):
    account: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class RegisterRequest(BaseModel):
    account: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=6, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    user: UserInfo


class TrainingSessionCreate(BaseModel):
    mode: InterviewMode
    position: str | None = Field(default=None, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    learning_module: str | None = Field(default=None, max_length=80)
    learning_module_title: str | None = Field(default=None, max_length=120)
    question_mix: QuestionMix | None = None


class TrainingSessionResponse(BaseModel):
    session_id: str
    mode: InterviewMode
    position: str | None = None
    company: str | None = None
    learning_module: str | None = None
    learning_module_title: str | None = None
    question_mix: QuestionMix | None = None
    status: str
    created_at: datetime


class TrainingSessionUpdate(BaseModel):
    position: str | None = Field(default=None, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    learning_module: str | None = Field(default=None, max_length=80)
    learning_module_title: str | None = Field(default=None, max_length=120)
    question_mix: QuestionMix | None = None


class MaterialUploadResponse(BaseModel):
    material_id: str
    session_id: str
    material_type: Literal["resume", "jd", "business_plan", "pitch_ppt", "project_intro"]
    filename: str
    mime_type: str
    size_bytes: int
    parse_status: Literal["parsed", "failed", "pending"]
    parse_error: str | None = None
    created_at: datetime


class QuestionOption(BaseModel):
    key: str
    text: str


class ExamQuestion(BaseModel):
    question_id: str
    question_type: QuestionType
    content: str
    options: list[QuestionOption] = Field(default_factory=list)


class GenerateExamRequest(BaseModel):
    session_id: str
    position: str = Field(min_length=1, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    difficulty: Difficulty = "medium"
    question_count: int = Field(default=10, ge=1, le=20)
    learning_module: str | None = Field(default=None, max_length=80)
    learning_module_title: str | None = Field(default=None, max_length=120)
    question_mix: QuestionMix | None = None

    @model_validator(mode="after")
    def validate_mix(self) -> "GenerateExamRequest":
        if self.question_mix is not None:
            total = self.question_mix.total()
            if total <= 0:
                raise ValueError("question_mix 至少需要包含一道题")
            self.question_count = total
        return self


class ExamPaperResponse(BaseModel):
    exam_id: str
    session_id: str
    title: str
    questions: list[ExamQuestion] = Field(default_factory=list)


class SubmittedAnswer(BaseModel):
    question_id: str
    answer: str | list[str]


class ExamSubmissionRequest(BaseModel):
    session_id: str
    exam_id: str
    answers: list[SubmittedAnswer] = Field(default_factory=list)


class ExamResultResponse(BaseModel):
    exam_id: str
    score: Score
    question_results: list[dict[str, Any]] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class QuestionResponse(BaseModel):
    question_id: str
    question: str


class EvaluationResponse(BaseModel):
    question_id: str
    score: Score
    dimension_scores: dict[str, Score] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    need_followup: bool = False
    followup_question: str | None = None


class InterviewMessageRequest(BaseModel):
    session_id: str
    question_id: str | None = None
    answer: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def validate_answer_pair(self) -> "InterviewMessageRequest":
        has_question = self.question_id is not None
        has_answer = self.answer is not None
        if has_question != has_answer:
            raise ValueError("question_id 和 answer 必须同时提供")
        if self.answer is not None and not self.answer.strip():
            raise ValueError("answer 不能为空")
        return self


class InterviewMessageResponse(BaseModel):
    interview_id: str
    evaluation: EvaluationResponse | None = None
    next_question: QuestionResponse
    is_followup: bool = False


class SimulationMessage(BaseModel):
    message_id: str
    speaker: Literal[
        "interviewer",
        "user",
        "candidate_logic",
        "candidate_collaboration",
        "candidate_challenger",
    ]
    display_name: str
    content: str = Field(min_length=1, max_length=10000)
    reply_to: str | None = None


class EvidenceReference(BaseModel):
    dimension: str
    quote: str
    rationale: str


class SimulationEvaluation(BaseModel):
    overall_score: Score
    dimension_scores: dict[str, Score]
    evidence: list[EvidenceReference]
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class SimulationStartRequest(BaseModel):
    session_id: str
    mode: SimulationMode
    stress_level: StressLevel | None = None


class SimulationHandleMessageRequest(BaseModel):
    session_id: str
    turn_id: str
    message: str = Field(min_length=1, max_length=10000)


class SimulationFinishRequest(BaseModel):
    session_id: str


class SimulationGenerateReportRequest(BaseModel):
    session_id: str


class SimulationTurnResponse(BaseModel):
    interview_id: str
    turn_id: str
    session_id: str
    mode: SimulationMode
    stage: SimulationStage
    status: Literal["active", "paused", "completed"] = "active"
    stress_level: StressLevel | None = None
    messages: list[SimulationMessage] = Field(min_length=1)
    control_acknowledged: bool = False


class SimulationFinishResponse(BaseModel):
    session_id: str
    mode: SimulationMode
    status: Literal["completed"] = "completed"
    evaluation: SimulationEvaluation


class ReportGenerateRequest(BaseModel):
    session_id: str


class ReportResponse(BaseModel):
    session_id: str
    mode: InterviewMode
    overall_score: Score
    dimension_scores: dict[str, Score] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    charts: dict[str, Any] = Field(default_factory=dict)
    summary: str


class ReportListItem(ReportResponse):
    generated_at: datetime
    position: str | None = None
    company: str | None = None
    learning_module_title: str | None = None


class FavoriteQuestionCreate(BaseModel):
    question: ExamQuestion


class FavoriteQuestionResponse(BaseModel):
    favorite_id: str
    question_id: str
    question_type: QuestionType
    content: str
    question: ExamQuestion
    created_at: datetime
