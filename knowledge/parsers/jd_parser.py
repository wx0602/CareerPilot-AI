from __future__ import annotations

import re
from typing import Any

from .resume_parser import extract_skills


def _collect_after_heading(text: str, headings: tuple[str, ...]) -> list[str]:
    lines = [line.strip(" \t-•·") for line in text.splitlines() if line.strip()]
    result: list[str] = []
    collecting = False
    for line in lines:
        if any(heading in line for heading in headings):
            collecting = True
            continue
        if collecting and re.match(r"^(岗位|职位|任职|工作|加分|福利).{0,10}[：:]?$", line):
            break
        if collecting:
            result.append(line)
    return result[:30]


def parse_jd_text(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = ""
    for line in lines[:10]:
        match = re.search(r"(?:岗位|职位|招聘职位|岗位名称)[：:]\s*(.+)", line)
        if match:
            title = match.group(1).strip()
            break
    if not title and lines:
        title = lines[0][:80]
    skills = extract_skills(text)
    education = next((line for line in lines if re.search(r"本科|硕士|博士|大专|学历", line)), "")
    experience = next((line for line in lines if re.search(r"\d+\s*年.*经验|经验.*\d+\s*年", line)), "")
    return {
        "job_title": title,
        "required_skills": skills,
        "responsibilities": _collect_after_heading(text, ("岗位职责", "工作职责", "职位职责")),
        "requirements": _collect_after_heading(text, ("任职要求", "岗位要求", "职位要求")),
        "education_requirement": education,
        "experience_requirement": experience,
    }
