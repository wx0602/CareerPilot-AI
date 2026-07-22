from __future__ import annotations

import io
import sys
from pathlib import Path
from urllib.error import HTTPError

import pytest

from app.core.config import Settings
from app.services.job_recommendations import (
    CandidateProfileBuilder,
    JSearchAPIError,
    JSearchConfigurationError,
    JSearchJobSource,
    JSearchTimeoutError,
    JobMatcher,
    JobNormalizer,
    JobRecommendationService,
    SeedJobSource,
)
from models import JobCandidateProfile


ROOT = Path(__file__).resolve().parents[2]
AI_CORE = ROOT / "ai-core"
if str(AI_CORE) not in sys.path:
    sys.path.insert(0, str(AI_CORE))

from agents.supervisor_agent import SupervisorAgent  # noqa: E402


def profile(**updates) -> JobCandidateProfile:
    values = {
        "target_position": "Java 后端工程师",
        "expected_city": "上海",
        "expected_salary_min": 20_000,
        "expected_salary_max": 30_000,
        "expected_salary_currency": "CNY",
        "expected_salary_period": "MONTH",
        "education": "本科",
        "years_of_experience": 2,
        "core_skills": ["Java", "Spring Boot"],
        "project_experience": ["商城系统"],
        "weak_skills": ["Kubernetes"],
        "recent_report_score": 100,
        "source": "combined",
    }
    values.update(updates)
    return JobCandidateProfile.model_validate(values)


def raw_job(**updates):
    values = {
        "job_id": "job-1",
        "job_title": "Java 后端工程师",
        "employer_name": "示例科技",
        "job_city": "上海",
        "job_description": "负责 Java、Spring Boot 服务开发，要求本科。",
        "job_employment_type": "FULLTIME",
        "job_posted_at_datetime_utc": "2026-07-17T00:00:00Z",
        "job_min_salary": 240_000,
        "job_max_salary": 360_000,
        "job_salary_period": "YEAR",
        "job_salary_currency": "CNY",
        "job_apply_link": "https://jobs.example.com/1",
        "job_publisher": "Example Jobs",
        "job_required_skills": ["Java", "Spring Boot"],
        "job_required_education": {"bachelors_degree": True},
        "job_required_experience": {"required_experience_in_months": 24},
    }
    values.update(updates)
    return values


def test_missing_jsearch_environment_variable():
    settings = Settings(
        database_url="sqlite:///:memory:",
        provider_mode="stub",
        jsearch_api_key=None,
    )
    source = JSearchJobSource(api_key=settings.jsearch_api_key)
    with pytest.raises(JSearchConfigurationError):
        source.search(profile())


def test_jsearch_normal_response_passes_server_side_key():
    captured = {}

    def transport(url, headers, timeout):
        captured.update(url=url, headers=headers, timeout=timeout)
        return {"status": "OK", "data": {"jobs": [raw_job()], "cursor": "next"}}

    source = JSearchJobSource(api_key="server-secret", transport=transport, timeout_seconds=3)
    result = source.search(profile())
    assert result[0]["job_id"] == "job-1"
    assert captured["headers"] == {"x-api-key": "server-secret"}
    assert captured["url"].startswith(
        "https://api.openwebninja.com/jsearch/search-v2?query="
    )
    assert "Java+%E5%90%8E%E7%AB%AF%E5%B7%A5%E7%A8%8B%E5%B8%88" in captured["url"]
    assert "page=" not in captured["url"]
    assert "num_pages=" not in captured["url"]
    assert "cursor=" not in captured["url"]
    assert captured["timeout"] == 3


def test_jsearch_search_v2_cursor_is_returned_and_can_be_sent():
    captured = {}

    def transport(url, headers, timeout):
        captured.update(url=url, headers=headers, timeout=timeout)
        return {
            "status": "OK",
            "data": {"jobs": [raw_job()], "cursor": "next cursor/+"},
        }

    source = JSearchJobSource(api_key="key", transport=transport)
    page = source.search_page(profile(), cursor="current cursor/+")

    assert page.next_cursor == "next cursor/+"
    assert page.jobs[0]["job_id"] == "job-1"
    assert "cursor=current+cursor%2F%2B" in captured["url"]


def test_jsearch_http_error_returns_provider_message_without_leaking_key():
    api_key = "server-secret"

    def transport(url, headers, timeout):
        body = b'{"message":"Invalid key server-secret"}'
        raise HTTPError(url, 401, "Unauthorized", {}, io.BytesIO(body))

    source = JSearchJobSource(api_key=api_key, transport=transport)
    with pytest.raises(JSearchAPIError, match=r"^Invalid key \[REDACTED\]$") as exc_info:
        source.search(profile())
    assert api_key not in str(exc_info.value)


def test_jsearch_timeout_is_translated():
    def transport(url, headers, timeout):
        raise TimeoutError

    source = JSearchJobSource(api_key="key", transport=transport)
    with pytest.raises(JSearchTimeoutError):
        source.search(profile())


def test_jsearch_empty_result_returns_empty_list():
    source = JSearchJobSource(
        api_key="key",
        transport=lambda url, headers, timeout: {
            "status": "OK",
            "data": {"jobs": [], "cursor": None},
        },
    )
    assert source.search(profile()) == []


def test_search_v2_fields_are_normalized():
    job = JobNormalizer().normalize(
        raw_job(
            job_required_skills=None,
            required_technologies=["Python", "FastAPI"],
            preferred_technologies=["Docker"],
            job_required_education=None,
            education_required={"level": "bachelor", "field": "computer science"},
            job_required_experience=None,
            required_experience_years=3,
        )
    )

    assert job.required_skills[:3] == ["Python", "FastAPI", "Docker"]
    assert job.education_required == "bachelor / computer science"
    assert job.min_experience_years == 3


def test_missing_salary_is_not_invented():
    job = JobNormalizer().normalize(
        raw_job(job_min_salary=None, job_max_salary=None, job_salary_period=None)
    )
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_display == "薪资未公开"


def test_job_deduplication_keeps_more_complete_record():
    incomplete = raw_job(job_id="first", job_description="", job_apply_link="")
    complete = raw_job(job_id="second")
    jobs = JobNormalizer().normalize_many([incomplete, complete])
    assert len(jobs) == 1
    assert jobs[0].job_id == "second"


def test_match_score_uses_all_weighted_dimensions():
    job = JobNormalizer().normalize(raw_job())
    result = JobMatcher().match(profile(), job)
    assert result["match_score"] == 100
    assert result["matched_skills"] == ["Java", "Spring Boot"]
    assert result["missing_skills"] == []


def test_resume_and_report_are_merged():
    class FakeAIProvider:
        def build_candidate_profile(self, request):
            assert request["mode"] == "job_recommendation"
            return {
                "target_position": "Java 后端工程师",
                "expected_city": "",
                "expected_salary_min": None,
                "expected_salary_max": None,
                "expected_salary_currency": "CNY",
                "expected_salary_period": "MONTH",
                "education": "本科",
                "years_of_experience": 2,
                "core_skills": request["resume_structured"]["skills"],
                "project_experience": request["resume_structured"]["project_experience"],
                "weak_skills": [],
                "recent_report_score": request["recent_report"]["overall_score"],
                "source": request["source"],
            }

    contexts = [
        {
            "source_type": "resume",
            "text": "Java 后端工程师，参与商城系统。",
            "metadata": {
                "structured_data": {
                    "skills": ["Java", "Spring Boot"],
                    "project_experience": ["商城系统"],
                    "education": ["本科"],
                }
            },
        }
    ]
    report = {"overall_score": 82, "weaknesses": ["Kubernetes"]}
    result = CandidateProfileBuilder(FakeAIProvider()).build(
        source="combined",
        resume_contexts=contexts,
        recent_report=report,
    )
    assert result.core_skills == ["Java", "Spring Boot"]
    assert result.project_experience == ["商城系统"]
    assert result.weak_skills == ["Kubernetes"]
    assert result.recent_report_score == 82


def test_supervisor_routes_job_recommendation_mode():
    result = SupervisorAgent()(
        {
            "task_type": "build_candidate_profile",
            "request": {"mode": "job_recommendation"},
        }
    )
    assert result["next_agent"] == "job_recommendation_agent"


class FakeSeedSource:
    metadata = {"fallback_policy": {"minimum_results": 5}}

    def __init__(self, jobs=None):
        self.jobs = jobs or []

    def load(self):
        return list(self.jobs)


class NoopExplainer:
    def explain_job_recommendations(self, request):
        return {"explanations": []}


class StaticJobSource:
    def __init__(self, jobs=None, error=None):
        self.jobs = jobs or []
        self.error = error

    def search(self, candidate_profile):
        if self.error:
            raise self.error
        return list(self.jobs)


def recommendation_service(*, jobs=None, error=None, seeds=None, link_checker=None):
    return JobRecommendationService(
        job_source=StaticJobSource(jobs, error),
        ai_provider=NoopExplainer(),
        seed_source=seeds or FakeSeedSource(),
        link_checker=link_checker or (lambda url: "active"),
    )


def test_real_seed_library_loads_all_official_jobs_without_salary_invention():
    rows = SeedJobSource().load()
    jobs = JobNormalizer().normalize_seed_many(rows)

    assert len(jobs) == 12
    assert all(job.apply_link.startswith("https://") for job in jobs)
    assert all(job.salary_display == "薪资未公开" for job in jobs)


def test_strict_zero_relaxes_salary_and_experience_first():
    jobs = [
        raw_job(
            job_id=f"relaxed-{index}",
            job_title=f"Java 后端工程师 {index}",
            employer_name=f"企业 {index}",
            job_apply_link=f"https://jobs.example.com/relaxed/{index}",
            job_min_salary=None,
            job_max_salary=None,
            job_salary_period=None,
            job_required_experience={"required_experience_in_months": 60},
        )
        for index in range(5)
    ]
    result = recommendation_service(jobs=jobs).recommend_with_metadata(profile())

    assert result.match_mode == "relaxed_salary_experience"
    assert len(result.jobs) == 5
    assert all(job["fallback"] is False for job in result.jobs)
    assert all(job["salary_display"] == "薪资未公开" for job in result.jobs)


def test_relaxation_order_moves_from_city_to_job_synonyms():
    city_jobs = [
        raw_job(
            job_id=f"city-{index}",
            job_title=f"Java 后端工程师 {index}",
            employer_name=f"异地企业 {index}",
            job_city="北京",
            job_apply_link=f"https://jobs.example.com/city/{index}",
        )
        for index in range(5)
    ]
    city_result = recommendation_service(jobs=city_jobs).recommend_with_metadata(profile())
    assert city_result.match_mode == "relaxed_city"

    synonym_jobs = [
        raw_job(
            job_id=f"synonym-{index}",
            job_title=f"后端工程师 {index}",
            employer_name=f"同义词企业 {index}",
            job_city="北京",
            job_apply_link=f"https://jobs.example.com/synonym/{index}",
            job_required_skills=["Python"],
        )
        for index in range(5)
    ]
    synonym_result = recommendation_service(jobs=synonym_jobs).recommend_with_metadata(
        profile(target_position="服务端开发工程师")
    )
    assert synonym_result.match_mode == "expanded_synonyms"


def test_crawler_failure_uses_seed_top_five_and_never_returns_empty():
    result = recommendation_service(
        error=JSearchTimeoutError("timeout"),
        seeds=SeedJobSource(),
    ).recommend_with_metadata(
        profile(target_position="大模型算法工程师", core_skills=["LLM", "NLP", "Agent"])
    )

    assert result.match_mode == "seed_fallback"
    assert len(result.jobs) == 5
    assert all(job["fallback"] is True for job in result.jobs)
    assert all(job["fallback_reason"] for job in result.jobs)
    assert all("matched_skills" in job and "missing_skills" in job for job in result.jobs)


def test_inactive_job_link_is_demoted_without_removing_other_jobs():
    jobs = [
        raw_job(
            job_id=f"link-{index}",
            job_title=f"Java 后端工程师 {index}",
            employer_name=f"链接企业 {index}",
            job_apply_link=f"https://jobs.example.com/{index}",
        )
        for index in range(6)
    ]
    result = recommendation_service(
        jobs=jobs,
        link_checker=lambda url: "inactive" if url.endswith("/0") else "active",
    ).recommend_with_metadata(profile())

    assert len(result.jobs) == 6
    assert result.jobs[-1]["job_id"] == "link-0"
    assert result.jobs[-1]["link_status"] == "inactive"
    assert all(job["job_id"] != "link-0" for job in result.jobs[:-1])


def test_live_and_seed_jobs_are_merged_and_live_duplicate_wins():
    normalizer = JobNormalizer()
    seed = normalizer.normalize_seed(SeedJobSource().load()[0])
    live = normalizer.normalize(
        raw_job(
            job_id="live-bytedance",
            job_title=seed.title,
            employer_name=seed.company_name,
            job_city=seed.city,
            job_apply_link=seed.apply_link,
            job_publisher="实时企业官网爬虫",
        )
    )

    merged = normalizer.dedupe([seed, live])
    assert len(merged) == 1
    assert merged[0].job_id == "live-bytedance"
    assert merged[0].source_kind == "live"


def test_search_api_returns_non_empty_seed_fallback_on_crawler_failure(logged_in):
    client, headers = logged_in
    client.app.state.job_source = StaticJobSource(error=JSearchAPIError("crawler failed"))
    client.app.state.job_link_checker = lambda url: "active"

    response = client.post(
        "/api/job-recommendations/search",
        headers=headers,
        json={"profile": profile(target_position="大模型算法工程师").model_dump(mode="json")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["match_mode"] == "seed_fallback"
    assert payload["fallback_reason"]
    assert len(payload["jobs"]) == 5
    assert all(job["fallback"] is True for job in payload["jobs"])
    assert all(job["salary_display"] == "薪资未公开" for job in payload["jobs"])

    interview = client.post(
        "/api/job-recommendations/interview",
        headers=headers,
        json={
            "profile": profile(target_position="大模型算法工程师").model_dump(mode="json"),
            "job": payload["jobs"][0],
        },
    )
    assert interview.status_code == 200
    assert interview.json()["mode"] == "job"

    first_question = client.post(
        "/api/interviews/message",
        headers=headers,
        json={"session_id": interview.json()["session_id"]},
    )
    assert first_question.status_code == 200
