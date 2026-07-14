from __future__ import annotations

import re
from typing import Any


SKILLS = {
    "Java", "Python", "JavaScript", "TypeScript", "Vue", "React", "Spring",
    "Spring Boot", "MySQL", "PostgreSQL", "Redis", "MongoDB", "Docker",
    "Kubernetes", "Linux", "Git", "FastAPI", "Django", "Flask", "PyTorch",
    "TensorFlow", "Pandas", "NumPy", "SQL", "Figma", "Axure", "JMeter",
    "Selenium", "Pytest", "机器学习", "深度学习", "数据分析", "接口测试",
}


def extract_skills(text: str) -> list[str]:
    found: list[str] = []
    for skill in sorted(SKILLS):
        escaped = re.escape(skill)
        if re.fullmatch(r"[A-Za-z0-9 .+#-]+", skill):
            pattern = rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])"
        else:
            pattern = escaped
        if re.search(pattern, text, re.IGNORECASE):
            found.append(skill)
    return found


def _section_lines(text: str, keywords: tuple[str, ...]) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result: list[str] = []
    collecting = False
    heading_pattern = re.compile(r"^(教育|工作|项目|实习|技能|证书|自我评价|求职|个人).{0,8}$")
    for line in lines:
        if any(keyword in line for keyword in keywords):
            collecting = True
            continue
        if collecting and heading_pattern.match(line):
            break
        if collecting:
            result.append(line)
    return result[:30]


def parse_resume_text(text: str) -> dict[str, Any]:
    emails = list(dict.fromkeys(re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)))
    phones = list(dict.fromkeys(re.findall(r"(?<!\d)1[3-9]\d{9}(?!\d)", text)))
    found_skills = extract_skills(text)
    education = [
        line for line in text.splitlines()
        if re.search(r"大学|学院|本科|硕士|博士|大专|学历|专业", line)
    ][:12]
    return {
        "emails": emails,
        "phones": phones,
        "skills": found_skills,
        "education": education,
        "work_experience": _section_lines(text, ("工作经历", "实习经历")),
        "project_experience": _section_lines(text, ("项目经历", "项目经验")),
    }
