from __future__ import annotations

from typing import Any


def average_score(results: list[dict[str, Any]]) -> int:
    if not results:
        return 0
    total = sum(int(item.get("score", 0)) for item in results)
    return round(total / len(results))


def collect_weaknesses(results: list[dict[str, Any]], limit: int = 6) -> list[str]:
    # 优先从低分题的知识点提取弱项；题库没有知识点时再使用反馈文本兜底。
    seen: set[str] = set()
    weaknesses: list[str] = []
    for item in results:
        if int(item.get("score", 0)) >= 80:
            continue
        for point in item.get("knowledge_points", []) or []:
            text = str(point).strip()
            if text and text not in seen:
                seen.add(text)
                weaknesses.append(text)
        feedback = str(item.get("feedback", "")).strip()
        if not item.get("knowledge_points") and feedback and feedback not in seen:
            seen.add(feedback)
            weaknesses.append(feedback)
        if len(weaknesses) >= limit:
            break
    return weaknesses


def build_suggestions(weaknesses: list[str]) -> list[str]:
    if not weaknesses:
        return ["继续保持当前答题质量，并通过限时练习提升稳定性。"]
    return [f"针对“{item}”进行专项复盘，补充原理、典型场景和易错点。" for item in weaknesses]
