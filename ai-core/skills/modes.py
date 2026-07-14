from __future__ import annotations

from typing import Any

from skills.definitions import MODE_TO_INTERVIEW_SKILL, SKILLS


MODE_SKILLS: dict[str, dict[str, Any]] = {
    mode: {
        "name": SKILLS[skill_name].name,
        "description": SKILLS[skill_name].description,
        "dimensions": SKILLS[skill_name].dimensions,
    }
    for mode, skill_name in MODE_TO_INTERVIEW_SKILL.items()
}


def get_mode_skill(mode: str) -> dict[str, Any]:
    if mode not in MODE_SKILLS:
        raise ValueError(f"不支持的训练模式：{mode}")
    return MODE_SKILLS[mode]
