from __future__ import annotations

import json
import re
import socket
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from models import (
    JobCandidateProfile,
    RecommendationExplanationRequest,
    RecommendationExplanationResponse,
)


class JSearchConfigurationError(RuntimeError):
    pass


class JSearchTimeoutError(RuntimeError):
    pass


class JSearchAPIError(RuntimeError):
    pass


class SeedDataError(RuntimeError):
    pass


def _unique_strings(values: list[Any]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(str(value).split()).strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            unique.append(text)
    return unique


class ResumeParser:
    """复用材料解析结果，将一个或多个简历 Context 合并给画像 Agent。"""

    def parse_contexts(self, contexts: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
        resume_contexts = [item for item in contexts if item.get("source_type") == "resume"]
        text = "\n\n".join(str(item.get("text") or "") for item in resume_contexts).strip()
        structured_items = [
            item.get("metadata", {}).get("structured_data") or {} for item in resume_contexts
        ]
        merged: dict[str, Any] = {}
        for key in ("emails", "phones", "skills", "education", "work_experience", "project_experience"):
            merged[key] = _unique_strings(
                [value for item in structured_items for value in (item.get(key) or [])]
            )
        return text[:20000], merged


class CandidateProfileBuilder:
    def __init__(self, ai_provider: Any, resume_parser: ResumeParser | None = None):
        self.ai_provider = ai_provider
        self.resume_parser = resume_parser or ResumeParser()

    def build(
        self,
        *,
        source: str,
        resume_contexts: list[dict[str, Any]],
        recent_report: dict[str, Any] | None,
    ) -> JobCandidateProfile:
        if source in {"resume", "combined"} and not resume_contexts:
            raise ValueError("请先上传并成功解析 PDF 或 DOCX 简历")
        if source in {"recent_report", "combined"} and not recent_report:
            raise ValueError("暂无可用的笔试或面试报告")

        resume_text, structured = self.resume_parser.parse_contexts(resume_contexts)
        payload = {
            "mode": "job_recommendation",
            "source": source,
            "resume_text": resume_text,
            "resume_structured": structured,
            "recent_report": recent_report,
        }
        profile = JobCandidateProfile.model_validate(
            self.ai_provider.build_candidate_profile(payload)
        )

        updates: dict[str, Any] = {
            "source": source,
            "core_skills": _unique_strings(profile.core_skills),
            "project_experience": _unique_strings(profile.project_experience),
            "weak_skills": _unique_strings(profile.weak_skills),
            "expected_salary_currency": profile.expected_salary_currency.upper(),
        }
        if recent_report:
            updates["recent_report_score"] = recent_report.get("overall_score")
            updates["weak_skills"] = _unique_strings(
                [*updates["weak_skills"], *(recent_report.get("weaknesses") or [])]
            )
        return profile.model_copy(update=updates)


Transport = Callable[[str, dict[str, str], float], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class JSearchPage:
    jobs: list[dict[str, Any]]
    next_cursor: str | None


class JSearchJobSource:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str = "https://api.openwebninja.com/jsearch/search-v2",
        timeout_seconds: float = 10.0,
        transport: Transport | None = None,
    ):
        self.api_key = (api_key or "").strip()
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.transport = transport or self._request_json

    @staticmethod
    def _request_json(url: str, headers: dict[str, str], timeout: float) -> dict[str, Any]:
        request = Request(url, headers=headers, method="GET")
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed configured host
            return json.loads(response.read().decode("utf-8"))

    def _safe_provider_message(self, message: Any, fallback: str) -> str:
        text = str(message).strip() if message is not None else ""
        if not text:
            return fallback
        return text.replace(self.api_key, "[REDACTED]") if self.api_key else text

    def _http_error_message(self, exc: HTTPError) -> str:
        fallback = f"JSearch API 返回 HTTP {exc.code}"
        try:
            body = exc.read().decode("utf-8", errors="replace")
            payload = json.loads(body)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
            return fallback
        if not isinstance(payload, dict):
            return fallback
        return self._safe_provider_message(payload.get("message"), fallback)

    def search(
        self,
        profile: JobCandidateProfile,
        *,
        limit: int = 30,
        cursor: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.search_page(profile, limit=limit, cursor=cursor).jobs

    def search_page(
        self,
        profile: JobCandidateProfile,
        *,
        limit: int = 30,
        cursor: str | None = None,
    ) -> JSearchPage:
        if not self.api_key:
            raise JSearchConfigurationError("缺少 JSEARCH_API_KEY，暂时无法搜索真实岗位")
        query_parts = [profile.target_position.strip(), profile.expected_city.strip()]
        query = " ".join(part for part in query_parts if part)
        if not query:
            raise ValueError("请先填写目标岗位")
        query_params = {"query": query}
        if cursor:
            query_params["cursor"] = cursor
        params = urlencode(query_params)
        headers = {"x-api-key": self.api_key}
        try:
            payload = self.transport(f"{self.base_url}?{params}", headers, self.timeout_seconds)
        except (TimeoutError, socket.timeout) as exc:
            raise JSearchTimeoutError("JSearch API 请求超时，请稍后重试") from exc
        except HTTPError as exc:
            raise JSearchAPIError(self._http_error_message(exc)) from exc
        except URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise JSearchTimeoutError("JSearch API 请求超时，请稍后重试") from exc
            raise JSearchAPIError("无法连接 JSearch API") from exc
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise JSearchAPIError("JSearch API 返回了无效数据") from exc

        if payload.get("status") == "ERROR":
            raise JSearchAPIError(
                self._safe_provider_message(payload.get("message"), "JSearch API 请求失败")
            )
        response_data = payload.get("data") or {}
        if isinstance(response_data, dict):
            data = response_data.get("jobs") or []
            raw_cursor = response_data.get("cursor")
        else:
            # 兼容已有测试桩和旧版扁平响应，不影响 search-v2 的嵌套结构。
            data = response_data
            raw_cursor = payload.get("cursor")
        if not isinstance(data, list):
            raise JSearchAPIError("JSearch API 岗位数据格式不正确")
        next_cursor = str(raw_cursor).strip() if raw_cursor is not None else None
        return JSearchPage(
            jobs=[item for item in data[:limit] if isinstance(item, dict)],
            next_cursor=next_cursor or None,
        )


DEFAULT_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "job_seeds.json"


class SeedJobSource:
    """读取本地官方招聘页面种子，加载成功后复用内存副本。"""

    def __init__(self, path: str | Path = DEFAULT_SEED_PATH):
        self.path = Path(path)
        self._jobs: list[dict[str, Any]] | None = None
        self.metadata: dict[str, Any] = {}

    def load(self) -> list[dict[str, Any]]:
        if self._jobs is not None:
            return list(self._jobs)
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SeedDataError(f"岗位种子库加载失败：{exc}") from exc
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list) or not all(isinstance(item, dict) for item in jobs):
            raise SeedDataError("岗位种子库格式不正确")
        self.metadata = payload.get("metadata") or {}
        expected_count = self.metadata.get("record_count")
        if expected_count is not None and expected_count != len(jobs):
            raise SeedDataError("岗位种子库记录数与 metadata.record_count 不一致")
        self._jobs = jobs
        return list(self._jobs)


class JobLinkChecker:
    """只把明确的 404/410 判为失效；反爬或网络失败保留为未知。"""

    def __init__(self, timeout_seconds: float = 3.0):
        self.timeout_seconds = timeout_seconds

    def __call__(self, url: str) -> str:
        if not url or urlsplit(url).scheme not in {"http", "https"}:
            return "inactive"
        request = Request(
            url,
            headers={"User-Agent": "CareerPilot-AI/1.0 link-check"},
            method="HEAD",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                return "active" if 200 <= response.status < 400 else "unknown"
        except HTTPError as exc:
            return "inactive" if exc.code in {404, 410} else "unknown"
        except (OSError, TimeoutError, URLError, socket.timeout):
            return "unknown"


@dataclass(slots=True)
class NormalizedJob:
    job_id: str
    title: str
    company_name: str
    city: str
    description: str
    employment_type: str | None
    posted_at: str | None
    salary_min: float | None
    salary_max: float | None
    salary_currency: str | None
    salary_period: str | None
    salary_display: str
    apply_link: str
    data_source: str
    required_skills: list[str]
    education_required: str | None = None
    min_experience_years: float | None = None
    source_kind: str = "live"
    link_status: str = "unknown"


class JobNormalizer:
    PERIOD_MULTIPLIERS = {
        "HOUR": 2080,
        "DAY": 260,
        "WEEK": 52,
        "MONTH": 12,
        "YEAR": 1,
    }

    @staticmethod
    def _number(value: Any) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @classmethod
    def annualize(cls, value: float | None, period: str | None) -> float | None:
        if value is None:
            return None
        multiplier = cls.PERIOD_MULTIPLIERS.get(str(period or "").upper())
        return round(value * multiplier, 2) if multiplier else None

    @staticmethod
    def _salary_display(
        minimum: float | None, maximum: float | None, currency: str | None
    ) -> str:
        if minimum is None and maximum is None:
            return "薪资未公开"
        unit = (currency or "").upper()
        prefix = f"{unit} " if unit else ""
        if minimum is not None and maximum is not None:
            return f"{prefix}{minimum:,.0f}–{maximum:,.0f} / 年"
        if minimum is not None:
            return f"{prefix}{minimum:,.0f} 起 / 年"
        return f"{prefix}最高 {maximum:,.0f} / 年"

    @staticmethod
    def _skills(raw: dict[str, Any], description: str) -> list[str]:
        explicit_values: list[Any] = []
        for field in ("job_required_skills", "required_technologies", "preferred_technologies"):
            value = raw.get(field) or []
            explicit_values.extend(re.split(r"[,，;/]", value) if isinstance(value, str) else value)
        explicit = _unique_strings(explicit_values)
        try:
            from knowledge.parsers.resume_parser import extract_skills

            extracted = extract_skills(description)
        except ImportError:
            extracted = []
        # API 显式技能优先；例如已有 Spring Boot 时不再额外加入父级词 Spring。
        supplemental = [
            skill
            for skill in extracted
            if not any(skill.casefold() in item.casefold() for item in explicit)
        ]
        return _unique_strings([*explicit, *supplemental])

    def normalize(self, raw: dict[str, Any]) -> NormalizedJob:
        title = " ".join(str(raw.get("job_title") or "未命名岗位").split())
        company = " ".join(str(raw.get("employer_name") or "公司未公开").split())
        city = " ".join(
            str(raw.get("job_city") or raw.get("job_location") or "地点未公开").split()
        )
        description = str(raw.get("job_description") or "").strip()
        period = str(raw.get("job_salary_period") or "").upper() or None
        currency = str(raw.get("job_salary_currency") or "").upper() or None
        salary_min = self.annualize(self._number(raw.get("job_min_salary")), period)
        salary_max = self.annualize(self._number(raw.get("job_max_salary")), period)
        employment = raw.get("job_employment_type") or raw.get("job_employment_types")
        if isinstance(employment, list):
            employment = " / ".join(map(str, employment))
        experience = raw.get("job_required_experience") or {}
        months = self._number(experience.get("required_experience_in_months")) if isinstance(experience, dict) else None
        experience_years = self._number(raw.get("required_experience_years"))
        education = raw.get("job_required_education") or raw.get("education_required") or {}
        education_text = None
        if isinstance(education, dict):
            legacy_level = next((key for key, value in education.items() if value is True), None)
            v2_values = _unique_strings(
                [education.get("level"), education.get("field")]
            )
            education_text = legacy_level or (" / ".join(v2_values) if v2_values else None)
        elif education:
            education_text = str(education)
        apply_link = str(raw.get("job_apply_link") or raw.get("job_google_link") or "")
        job_id = str(raw.get("job_id") or "").strip()
        if not job_id:
            job_id = sha256(f"{title}|{company}|{city}|{apply_link}".encode()).hexdigest()[:20]
        return NormalizedJob(
            job_id=job_id,
            title=title,
            company_name=company,
            city=city,
            description=description,
            employment_type=str(employment) if employment else None,
            posted_at=str(
                raw.get("job_posted_at_datetime_utc") or raw.get("job_posted_at") or ""
            ) or None,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=currency,
            salary_period="YEAR" if salary_min is not None or salary_max is not None else None,
            salary_display=self._salary_display(salary_min, salary_max, currency),
            apply_link=apply_link,
            data_source=str(raw.get("job_publisher") or "JSearch"),
            required_skills=self._skills(raw, description),
            education_required=education_text,
            min_experience_years=(
                round(months / 12, 1) if months is not None else experience_years
            ),
        )

    def normalize_seed(self, raw: dict[str, Any]) -> NormalizedJob:
        salary = raw.get("salary") if isinstance(raw.get("salary"), dict) else {}
        cities = _unique_strings(raw.get("cities") or [])
        experience_text = str(raw.get("experience") or "")
        experience_match = re.search(r"(\d+(?:\.\d+)?)\s*年", experience_text)
        salary_min = self.annualize(self._number(salary.get("min")), salary.get("period"))
        salary_max = self.annualize(self._number(salary.get("max")), salary.get("period"))
        currency = str(salary.get("currency") or "").upper() or None
        description_parts = _unique_strings(
            [raw.get("requirements_summary"), raw.get("department")]
        )
        return NormalizedJob(
            job_id=str(raw.get("id") or "").strip(),
            title=" ".join(str(raw.get("title") or "未命名岗位").split()),
            company_name=" ".join(str(raw.get("company") or "公司未公开").split()),
            city=" / ".join(cities) if cities else "城市不限",
            description="；".join(description_parts),
            employment_type=str(raw.get("job_type") or "") or None,
            posted_at=str(raw.get("published_at") or "") or None,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=currency,
            salary_period="YEAR" if salary_min is not None or salary_max is not None else None,
            salary_display=self._salary_display(salary_min, salary_max, currency),
            apply_link=str(raw.get("source_url") or ""),
            data_source=str(raw.get("source") or "企业官方招聘"),
            required_skills=_unique_strings(raw.get("match_terms") or []),
            education_required=str(raw.get("education") or "") or None,
            min_experience_years=(
                float(experience_match.group(1)) if experience_match else None
            ),
            source_kind="seed",
        )

    @staticmethod
    def _canonical_link(job: NormalizedJob) -> str:
        parsed = urlsplit(job.apply_link)
        return urlunsplit(
            (parsed.scheme.casefold(), parsed.netloc.casefold(), parsed.path.rstrip("/"), parsed.query, "")
        )

    @classmethod
    def _same_job(cls, left: NormalizedJob, right: NormalizedJob) -> bool:
        same_identity = (
            left.title.casefold().strip(),
            left.company_name.casefold().strip(),
            left.city.casefold().strip(),
        ) == (
            right.title.casefold().strip(),
            right.company_name.casefold().strip(),
            right.city.casefold().strip(),
        )
        left_link, right_link = cls._canonical_link(left), cls._canonical_link(right)
        return same_identity or bool(left_link and left_link.casefold() == right_link.casefold())

    @staticmethod
    def _completeness(job: NormalizedJob) -> int:
        return sum(
            bool(value)
            for value in (job.description, job.apply_link, job.salary_min, job.salary_max)
        )

    def dedupe(self, jobs: list[NormalizedJob]) -> list[NormalizedJob]:
        selected: list[NormalizedJob] = []
        for job in jobs:
            current_index = next(
                (index for index, current in enumerate(selected) if self._same_job(current, job)),
                None,
            )
            if current_index is None:
                selected.append(job)
                continue
            current = selected[current_index]
            # 实时抓取记录优先；同源时保留信息更完整的记录。
            if current.source_kind == "seed" and job.source_kind == "live":
                selected[current_index] = job
            elif current.source_kind == job.source_kind and self._completeness(job) > self._completeness(current):
                selected[current_index] = job
        return selected

    def normalize_many(self, rows: list[dict[str, Any]]) -> list[NormalizedJob]:
        return self.dedupe([self.normalize(item) for item in rows])

    def normalize_seed_many(self, rows: list[dict[str, Any]]) -> list[NormalizedJob]:
        return self.dedupe([self.normalize_seed(item) for item in rows])


class JobMatcher:
    WEIGHTS = {
        "skills": 0.40,
        "direction": 0.20,
        "city": 0.10,
        "education_experience": 0.10,
        "salary": 0.10,
        "report": 0.10,
    }
    DIRECTION_SYNONYMS = {
        "backend": {"后端", "后台", "服务端", "backend", "server-side"},
        "frontend": {"前端", "web前端", "frontend", "web"},
        "llm": {"大模型", "llm", "生成式ai", "智能体", "agent"},
        "machine_learning": {"机器学习", "深度学习", "模型算法", "ai算法"},
        "algorithm": {"算法", "搜索算法", "地图算法", "slam"},
        "platform": {"平台工程", "基础设施", "云计算", "分布式计算", "运维平台"},
    }

    @staticmethod
    def _tokens(text: str) -> set[str]:
        latin = re.findall(r"[a-z0-9+#.]+", text.casefold())
        chinese = re.findall(r"[\u4e00-\u9fff]{2,}", text)
        return set(latin + chinese)

    def _direction_score(self, target: str, title: str) -> float:
        if not target:
            return 50
        if target.casefold() in title.casefold() or title.casefold() in target.casefold():
            return 100
        left, right = self._tokens(target), self._tokens(title)
        return 100 * len(left & right) / len(left | right) if left | right else 0

    @classmethod
    def _direction_labels(cls, text: str, *, expand_synonyms: bool) -> set[str]:
        lowered = text.casefold().replace(" ", "")
        labels: set[str] = set()
        for label, aliases in cls.DIRECTION_SYNONYMS.items():
            hits = {alias.casefold() for alias in aliases if alias.casefold().replace(" ", "") in lowered}
            if hits:
                labels.add(label if expand_synonyms else sorted(hits)[0])
        labels.update(re.findall(r"[a-z][a-z0-9+#.-]{1,}", text.casefold()))
        return labels

    @classmethod
    def direction_matches(
        cls, target: str, job: NormalizedJob, *, expand_synonyms: bool = False
    ) -> bool:
        if not target.strip():
            return True
        haystack = " ".join([job.title, *job.required_skills])
        target_text = target.casefold().replace(" ", "")
        haystack_text = haystack.casefold().replace(" ", "")
        if target_text in haystack_text or job.title.casefold().replace(" ", "") in target_text:
            return True
        left = cls._direction_labels(target, expand_synonyms=expand_synonyms)
        right = cls._direction_labels(haystack, expand_synonyms=expand_synonyms)
        return bool(left & right)

    @staticmethod
    def _city_score(expected: str, actual: str) -> float:
        if not expected:
            return 50
        if "remote" in actual.casefold() or "远程" in actual:
            return 100
        return 100 if expected.casefold() in actual.casefold() else 0

    @staticmethod
    def _education_rank(text: str) -> int | None:
        lowered = text.casefold()
        ranks = (("博士", 4), ("硕士", 3), ("本科", 2), ("学士", 2), ("大专", 1), ("college", 1), ("bachelor", 2), ("master", 3), ("phd", 4))
        return next((rank for keyword, rank in ranks if keyword in lowered), None)

    def _education_experience_score(self, profile: JobCandidateProfile, job: NormalizedJob) -> float:
        scores: list[float] = []
        required_rank = self._education_rank(job.education_required or job.description)
        profile_rank = self._education_rank(profile.education)
        if required_rank is not None:
            scores.append(100 if profile_rank is not None and profile_rank >= required_rank else 0)
        if job.min_experience_years is not None:
            scores.append(
                100
                if profile.years_of_experience is not None
                and profile.years_of_experience >= job.min_experience_years
                else 0
            )
        return sum(scores) / len(scores) if scores else 50

    @staticmethod
    def _annual_expected(profile: JobCandidateProfile, value: float | None) -> float | None:
        return JobNormalizer.annualize(value, profile.expected_salary_period)

    def _salary_score(self, profile: JobCandidateProfile, job: NormalizedJob) -> float:
        expected_min = self._annual_expected(profile, profile.expected_salary_min)
        expected_max = self._annual_expected(profile, profile.expected_salary_max)
        if expected_min is None and expected_max is None:
            return 50
        if job.salary_min is None and job.salary_max is None:
            return 50
        if job.salary_currency and job.salary_currency != profile.expected_salary_currency.upper():
            return 50
        left_min = expected_min or 0
        left_max = expected_max or float("inf")
        right_min = job.salary_min or 0
        right_max = job.salary_max or float("inf")
        return 100 if max(left_min, right_min) <= min(left_max, right_max) else 0

    def city_matches(self, profile: JobCandidateProfile, job: NormalizedJob) -> bool:
        if not profile.expected_city.strip() or job.city == "城市不限":
            return True
        return self._city_score(profile.expected_city, job.city) == 100

    @staticmethod
    def experience_matches(profile: JobCandidateProfile, job: NormalizedJob) -> bool:
        if profile.years_of_experience is None or job.min_experience_years is None:
            return True
        return profile.years_of_experience >= job.min_experience_years

    def salary_matches(self, profile: JobCandidateProfile, job: NormalizedJob) -> bool:
        expects_salary = (
            profile.expected_salary_min is not None or profile.expected_salary_max is not None
        )
        if not expects_salary:
            return True
        if job.salary_min is None and job.salary_max is None:
            return False
        return self._salary_score(profile, job) == 100

    @classmethod
    def _canonical_skill(cls, skill: str) -> str:
        lowered = skill.casefold().replace(" ", "")
        for label, aliases in cls.DIRECTION_SYNONYMS.items():
            if lowered in {alias.casefold().replace(" ", "") for alias in aliases}:
                return label
        return lowered

    def match(self, profile: JobCandidateProfile, job: NormalizedJob) -> dict[str, Any]:
        profile_map = {self._canonical_skill(skill): skill for skill in profile.core_skills}
        matched = [
            profile_map[self._canonical_skill(skill)]
            for skill in job.required_skills
            if self._canonical_skill(skill) in profile_map
        ]
        missing = [
            skill
            for skill in job.required_skills
            if self._canonical_skill(skill) not in profile_map
        ]
        skill_score = 100 * len(matched) / len(job.required_skills) if job.required_skills else 50
        components = {
            "skills": skill_score,
            "direction": self._direction_score(profile.target_position, job.title),
            "city": self._city_score(profile.expected_city, job.city),
            "education_experience": self._education_experience_score(profile, job),
            "salary": self._salary_score(profile, job),
            "report": profile.recent_report_score if profile.recent_report_score is not None else 50,
        }
        score = round(sum(components[key] * self.WEIGHTS[key] for key in self.WEIGHTS))
        reason = f"岗位方向与画像综合匹配，技能已覆盖 {len(matched)}/{len(job.required_skills)} 项。"
        suggestions = [f"通过项目或课程补强 {skill}" for skill in missing[:3]]
        return {
            "job_id": job.job_id,
            "title": job.title,
            "company_name": job.company_name,
            "city": job.city,
            "description": job.description,
            "employment_type": job.employment_type,
            "posted_at": job.posted_at,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_currency": job.salary_currency,
            "salary_period": job.salary_period,
            "salary_display": job.salary_display,
            "apply_link": job.apply_link,
            "data_source": job.data_source,
            "required_skills": job.required_skills,
            "match_score": max(0, min(100, score)),
            "recommendation_reason": reason,
            "matched_skills": _unique_strings(matched),
            "missing_skills": _unique_strings(missing),
            "improvement_suggestions": suggestions,
            "fallback": False,
            "match_mode": "strict",
            "fallback_reason": None,
            "link_status": job.link_status,
            "source_kind": job.source_kind,
        }

    def rank(
        self,
        profile: JobCandidateProfile,
        jobs: list[NormalizedJob],
        *,
        limit: int | None = 10,
    ) -> list[dict[str, Any]]:
        matches = [self.match(profile, job) for job in jobs]
        matches.sort(
            key=lambda item: (
                item["link_status"] != "inactive",
                item["match_score"],
                item["source_kind"] == "live",
            ),
            reverse=True,
        )
        return matches[:limit] if limit is not None else matches

    def rank_seed_fallback(
        self,
        profile: JobCandidateProfile,
        jobs: list[NormalizedJob],
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        profile_skills = {self._canonical_skill(skill) for skill in profile.core_skills}

        def relevance(job: NormalizedJob) -> float:
            left = self._direction_labels(profile.target_position, expand_synonyms=True)
            right = self._direction_labels(
                " ".join([job.title, *job.required_skills]), expand_synonyms=True
            )
            direction_score = 100 * len(left & right) / len(left | right) if left | right else 0
            job_skills = {self._canonical_skill(skill) for skill in job.required_skills}
            skill_score = (
                100 * len(profile_skills & job_skills) / len(job_skills)
                if job_skills
                else 0
            )
            return direction_score * 0.6 + skill_score * 0.4

        matches_by_id = {item["job_id"]: item for item in self.rank(profile, jobs, limit=None)}
        ordered_jobs = sorted(
            jobs,
            key=lambda job: (
                job.link_status != "inactive",
                relevance(job),
                matches_by_id[job.job_id]["match_score"],
            ),
            reverse=True,
        )
        return [matches_by_id[job.job_id] for job in ordered_jobs[:limit]]


class RecommendationExplainer:
    def __init__(self, ai_provider: Any):
        self.ai_provider = ai_provider

    def enrich(self, profile: JobCandidateProfile, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        request = RecommendationExplanationRequest(
            profile=profile,
            jobs=[
                {
                    "job_id": item["job_id"],
                    "title": item["title"],
                    "company_name": item["company_name"],
                    "match_score": item["match_score"],
                    "matched_skills": item["matched_skills"],
                    "missing_skills": item["missing_skills"],
                }
                for item in matches
            ],
        )
        try:
            response = RecommendationExplanationResponse.model_validate(
                self.ai_provider.explain_job_recommendations(request.model_dump(mode="json"))
            )
        except Exception:
            return matches
        explanations = {item.job_id: item for item in response.explanations}
        for match in matches:
            explanation = explanations.get(match["job_id"])
            if explanation:
                match["recommendation_reason"] = explanation.recommendation_reason
                match["improvement_suggestions"] = explanation.improvement_suggestions
        return matches


@dataclass(slots=True)
class RecommendationResult:
    jobs: list[dict[str, Any]]
    match_mode: str
    fallback_reason: str | None


class JobRecommendationService:
    def __init__(
        self,
        *,
        job_source: JSearchJobSource,
        ai_provider: Any,
        normalizer: JobNormalizer | None = None,
        matcher: JobMatcher | None = None,
        seed_source: SeedJobSource | None = None,
        link_checker: Callable[[str], str] | None = None,
    ):
        self.job_source = job_source
        self.normalizer = normalizer or JobNormalizer()
        self.matcher = matcher or JobMatcher()
        self.seed_source = seed_source or SeedJobSource()
        self.link_checker = link_checker or JobLinkChecker()
        self.explainer = RecommendationExplainer(ai_provider)

    def _verify_links(self, profile: JobCandidateProfile, jobs: list[NormalizedJob]) -> None:
        for job in jobs:
            if not job.apply_link:
                job.link_status = "inactive"
        preliminary = self.matcher.rank(profile, jobs, limit=15)
        selected_ids = {item["job_id"] for item in preliminary}
        selected = [job for job in jobs if job.job_id in selected_ids and job.apply_link]
        if not selected:
            return

        def check(job: NormalizedJob) -> tuple[NormalizedJob, str]:
            try:
                status = self.link_checker(job.apply_link)
            except Exception:
                status = "unknown"
            return job, status if status in {"active", "inactive", "unknown"} else "unknown"

        with ThreadPoolExecutor(max_workers=min(5, len(selected))) as executor:
            for job, status in executor.map(check, selected):
                job.link_status = status

    def _rank_stage(
        self,
        profile: JobCandidateProfile,
        jobs: list[NormalizedJob],
        *,
        match_mode: str,
        fallback_reason: str | None,
        fallback: bool,
        limit: int,
        seed_priority: bool = False,
    ) -> RecommendationResult:
        self._verify_links(profile, jobs)
        matches = (
            self.matcher.rank_seed_fallback(profile, jobs, limit=limit)
            if seed_priority
            else self.matcher.rank(profile, jobs, limit=limit)
        )
        for match in matches:
            match["match_mode"] = match_mode
            match["fallback_reason"] = fallback_reason
            match["fallback"] = fallback
            match.pop("source_kind", None)
        return RecommendationResult(
            jobs=self.explainer.enrich(profile, matches),
            match_mode=match_mode,
            fallback_reason=fallback_reason,
        )

    def _seed_fallback(
        self,
        profile: JobCandidateProfile,
        seed_jobs: list[NormalizedJob],
        reason: str,
    ) -> RecommendationResult:
        return self._rank_stage(
            profile,
            seed_jobs,
            match_mode="seed_fallback",
            fallback_reason=reason,
            fallback=True,
            limit=5,
            seed_priority=True,
        )

    def recommend_with_metadata(self, profile: JobCandidateProfile) -> RecommendationResult:
        if not profile.target_position.strip():
            raise ValueError("请先填写目标岗位")

        seed_error: SeedDataError | None = None
        try:
            seed_rows = self.seed_source.load()
            seed_jobs = self.normalizer.normalize_seed_many(seed_rows)
        except SeedDataError as exc:
            seed_error = exc
            seed_jobs = []

        live_error: RuntimeError | None = None
        try:
            live_rows = self.job_source.search(profile)
            live_jobs = self.normalizer.normalize_many(live_rows)
        except (JSearchConfigurationError, JSearchTimeoutError, JSearchAPIError) as exc:
            live_error = exc
            live_jobs = []

        if live_error is not None and seed_jobs:
            return self._seed_fallback(
                profile,
                seed_jobs,
                "实时岗位源不可用，已使用本地真实岗位种子库。",
            )
        if live_error is not None and not seed_jobs:
            raise live_error
        if not live_jobs and seed_jobs:
            return self._seed_fallback(
                profile,
                seed_jobs,
                "实时岗位源未返回岗位，已使用本地真实岗位种子库。",
            )

        merged = self.normalizer.dedupe([*live_jobs, *seed_jobs])
        minimum_results = 5
        policy = self.seed_source.metadata.get("fallback_policy") or {}
        if isinstance(policy.get("minimum_results"), int):
            minimum_results = max(1, policy["minimum_results"])

        stages: list[tuple[str, str | None, list[NormalizedJob]]] = [
            (
                "strict",
                None,
                [
                    job
                    for job in merged
                    if self.matcher.direction_matches(profile.target_position, job)
                    and self.matcher.city_matches(profile, job)
                    and self.matcher.experience_matches(profile, job)
                    and self.matcher.salary_matches(profile, job)
                ],
            ),
            (
                "relaxed_salary_experience",
                "严格筛选结果不足 5 条，已放宽薪资和经验条件。",
                [
                    job
                    for job in merged
                    if self.matcher.direction_matches(profile.target_position, job)
                    and self.matcher.city_matches(profile, job)
                ],
            ),
            (
                "relaxed_city",
                "放宽薪资和经验后结果仍不足 5 条，已进一步放宽城市条件。",
                [
                    job
                    for job in merged
                    if self.matcher.direction_matches(profile.target_position, job)
                ],
            ),
            (
                "expanded_synonyms",
                "放宽城市后结果仍不足 5 条，已扩展岗位同义词。",
                [
                    job
                    for job in merged
                    if self.matcher.direction_matches(
                        profile.target_position, job, expand_synonyms=True
                    )
                ],
            ),
        ]
        for match_mode, reason, candidates in stages:
            if len(candidates) >= minimum_results:
                return self._rank_stage(
                    profile,
                    candidates,
                    match_mode=match_mode,
                    fallback_reason=reason,
                    fallback=False,
                    limit=10,
                )

        if seed_jobs:
            return self._seed_fallback(
                profile,
                seed_jobs,
                "分级放宽后仍不足 5 条，已按岗位方向和技能匹配度返回种子库 Top 5。",
            )

        widest = stages[-1][2]
        if widest:
            return self._rank_stage(
                profile,
                widest,
                match_mode="expanded_synonyms",
                fallback_reason=stages[-1][1],
                fallback=False,
                limit=10,
            )
        if seed_error is not None:
            raise seed_error
        return RecommendationResult(jobs=[], match_mode="no_match", fallback_reason=None)

    def recommend(self, profile: JobCandidateProfile) -> list[dict[str, Any]]:
        return self.recommend_with_metadata(profile).jobs
