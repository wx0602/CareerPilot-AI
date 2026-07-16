from __future__ import annotations

from collections.abc import Iterable

from models import SimulationEvaluation, SimulationMessage, StressLevel


GROUP_DIMENSIONS = (
    "逻辑",
    "表达",
    "参与度",
    "协作",
    "倾听",
    "领导力",
    "冲突处理",
    "总结能力",
)

STRESS_DIMENSIONS = (
    "稳定性",
    "逻辑一致性",
    "证据质量",
    "应变能力",
    "直接性",
    "可信度",
    "表达",
    "反思能力",
)

STRESS_LEVELS: tuple[StressLevel, ...] = ("light", "medium", "high")


def dimensions_for_mode(mode: str) -> tuple[str, ...]:
    if mode == "group_interview":
        return GROUP_DIMENSIONS
    if mode == "stress_interview":
        return STRESS_DIMENSIONS
    raise ValueError(f"不支持的模拟面试模式：{mode}")


def validate_evaluation(
    mode: str,
    evaluation: SimulationEvaluation,
    history: Iterable[SimulationMessage],
) -> None:
    required = set(dimensions_for_mode(mode))
    actual = set(evaluation.dimension_scores)
    if actual != required:
        missing = sorted(required - actual)
        extra = sorted(actual - required)
        raise ValueError(f"评分维度不完整，缺少={missing}，多余={extra}")

    user_statements = [item.content for item in history if item.speaker == "user"]
    if not user_statements:
        raise ValueError("没有用户真实发言，无法评分")

    evidence_dimensions = {item.dimension for item in evaluation.evidence}
    if not required <= evidence_dimensions:
        missing = sorted(required - evidence_dimensions)
        raise ValueError(f"以下评分维度缺少用户发言证据：{missing}")

    for item in evaluation.evidence:
        if item.dimension not in required:
            raise ValueError(f"证据引用了未知评分维度：{item.dimension}")
        if not any(item.quote in statement for statement in user_statements):
            raise ValueError(f"评分证据不是用户真实发言：{item.quote}")


def lower_stress_level(level: StressLevel | None) -> StressLevel:
    current = level or "medium"
    index = STRESS_LEVELS.index(current)
    return STRESS_LEVELS[max(0, index - 1)]


def detect_stress_control(message: str) -> str | None:
    normalized = "".join(message.strip().lower().split())
    if any(command in normalized for command in ("停止", "结束", "stop")):
        return "stop"
    if any(command in normalized for command in ("暂停", "pause")):
        return "pause"
    if any(command in normalized for command in ("降低压力", "压力降低", "轻一点")):
        return "lower"
    return None


def validate_safe_pressure(messages: Iterable[SimulationMessage]) -> None:
    forbidden = (
        "废物",
        "蠢货",
        "没用的人",
        "威胁你",
        "滚出去",
        "人格有问题",
    )
    for message in messages:
        if message.speaker == "interviewer" and any(term in message.content for term in forbidden):
            raise ValueError("压力面试输出包含侮辱、威胁或人格攻击")
