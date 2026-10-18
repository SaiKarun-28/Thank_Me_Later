"""
Section 4: Skill Normalization, Query Generation, Deduplication, and Hybrid Ranking Tests.
"""
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.conftest import MockLLMProvider
from app.section1_foundation_and_providers.schemas.job import JobPosting, SearchJobsRequest, JobSourceConfig
from app.section1_foundation_and_providers.schemas.resume import SearchProfile, TargetRole
from app.section4_ranking_and_search.services.queries import generate_search_queries
from app.section4_ranking_and_search.services.ranking import (
    calculate_heuristic_score,
    deduplicate_jobs,
    filter_recency_30_days,
    rank_and_enrich_jobs,
)
from app.section4_ranking_and_search.services.skills import (
    calculate_skill_overlap,
    normalize_skill,
)


def test_canonical_skill_normalization():
    """Verify skill alias resolution to canonical names."""
    assert normalize_skill("js") == "JavaScript"
    assert normalize_skill("javascript") == "JavaScript"
    assert normalize_skill("ts") == "TypeScript"
    assert normalize_skill("k8s") == "Kubernetes"
    assert normalize_skill("react.js") == "React"
    assert normalize_skill("node") == "Node.js"
    assert normalize_skill("aws") == "AWS"
    assert normalize_skill("postgres") == "PostgreSQL"
    assert normalize_skill("unknown_skill_xyz") == "unknown_skill_xyz"


def test_skill_overlap_calculation_with_aliases():
    """Verify skill overlap detection using canonical alias mapping and word boundaries."""
    candidate_skills = ["JavaScript", "Kubernetes", "Python", "GraphQL"]
    job_description = "We are seeking a developer proficient in JS and K8s to build modern cloud apps."

    score, matched, missing = calculate_skill_overlap(candidate_skills, job_description)

    # JS matches JavaScript, K8s matches Kubernetes
    assert "JavaScript" in matched
    assert "Kubernetes" in matched
    assert "Python" in missing
    assert "GraphQL" in missing
    assert score == 50.0  # 2 out of 4 matched


def test_generate_search_queries():
    """Verify 1-3 targeted queries generation from target roles and top skills."""
    profile = SearchProfile(
        target_roles=[
            TargetRole(role="Full Stack Engineer", confidence=0.95),
            TargetRole(role="Backend Engineer", confidence=0.85),
        ],
        skills=["Python", "FastAPI", "React"],
    )

    queries = generate_search_queries(profile)
    assert len(queries) >= 2
    assert "Full Stack Engineer" in queries
    assert "Backend Engineer" in queries
    # Top 3 queries max
    assert len(queries) <= 3


def test_deduplicate_jobs():
    """Verify deduplication by case- and whitespace-normalized (title, company, location)."""
    jobs = [
        JobPosting(id="1", title="Senior Engineer", company="Stripe", location="SF", apply_url="https://stripe.com/1", source="A"),
        JobPosting(id="2", title="senior engineer", company="stripe", location="sf ", apply_url="https://stripe.com/2", source="B"),
        JobPosting(id="3", title="Frontend Dev", company="Stripe", location="SF", apply_url="https://stripe.com/3", source="A"),
    ]

    deduped = deduplicate_jobs(jobs)
    assert len(deduped) == 2
    assert deduped[0].id == "1"
    assert deduped[1].id == "3"


def test_filter_recency_30_days():
    """Verify that jobs older than 30 days are excluded, while recent & undated are kept."""
    now = datetime.now(timezone.utc)
    recent_date = (now - timedelta(days=5)).isoformat()
    old_date = (now - timedelta(days=35)).isoformat()

    jobs = [
        JobPosting(id="recent", title="Job 1", company="A", apply_url="https://a.com/1", posted_date=recent_date, source="S"),
        JobPosting(id="old", title="Job 2", company="B", apply_url="https://b.com/1", posted_date=old_date, source="S"),
        JobPosting(id="undated", title="Job 3", company="C", apply_url="https://c.com/1", posted_date=None, source="S"),
    ]

    filtered = filter_recency_30_days(jobs)
    ids = [j.id for j in filtered]
    assert "recent" in ids
    assert "undated" in ids
    assert "old" not in ids


def test_heuristic_scoring_weights():
    """Verify that a job with high skill overlap and role match scores higher than an unrelated job."""
    profile = SearchProfile(
        target_roles=[TargetRole(role="Senior Backend Engineer", confidence=0.95)],
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        remote_preference="remote",
        experience_level="senior",
    )

    strong_fit = JobPosting(
        id="strong",
        title="Senior Backend Engineer",
        company="TechCorp",
        location="Remote",
        remote=True,
        description="Looking for Senior Backend Engineer with Python, FastAPI, Postgres, and Docker.",
        apply_url="https://techcorp.com/apply",
        source="Test",
    )

    weak_fit = JobPosting(
        id="weak",
        title="Junior Graphic Designer",
        company="DesignCo",
        location="New York, NY",
        remote=False,
        description="Create marketing graphics in Photoshop.",
        apply_url="https://designco.com/apply",
        source="Test",
    )

    strong_score, strong_matched, _ = calculate_heuristic_score(strong_fit, profile)
    weak_score, weak_matched, _ = calculate_heuristic_score(weak_fit, profile)

    assert strong_score > weak_score
    assert len(strong_matched) >= 3
    assert len(weak_matched) == 0


@pytest.mark.asyncio
async def test_rank_and_enrich_jobs_with_llm():
    """Verify funnel: heuristic score, Top 30 for LLM enrichment, and 50/50 final score combination."""
    profile = SearchProfile(
        target_roles=[TargetRole(role="Full Stack Engineer", confidence=0.9)],
        skills=["React", "Node.js", "TypeScript"],
    )

    # Create 35 test jobs to test Top 100 -> Top 30 funnel
    jobs = [
        JobPosting(
            id=f"job-{i}",
            title="Full Stack Engineer",
            company=f"Company {i}",
            location="Remote",
            remote=True,
            description="We need React and TypeScript engineers.",
            apply_url=f"https://company{i}.com/apply",
            source="Test",
        )
        for i in range(35)
    ]

    mock_llm = MockLLMProvider()
    # Mock LLM evaluation response
    mock_llm.json_completion = AsyncMock(
        return_value={
            "evaluations": [
                {
                    "id": f"job-{i}",
                    "match_score": 90.0,
                    "match_reason": "Exceptional alignment with full-stack requirements.",
                    "required_skills": ["React", "TypeScript", "Node.js"],
                }
                for i in range(35)
            ]
        }
    )

    ranked = await rank_and_enrich_jobs(jobs, profile, llm=mock_llm)

    # Returns Top 20
    assert len(ranked) == 20
    # Final score = 0.5 * heuristic + 0.5 * llm
    assert ranked[0].llm_score == 90.0
    assert ranked[0].final_score > 0
    assert "Exceptional alignment" in ranked[0].match_reason


@pytest.mark.asyncio
async def test_rank_and_enrich_fallback_without_llm():
    """Verify that when LLM is omitted or fails, 100% heuristic score is used cleanly."""
    profile = SearchProfile(
        target_roles=[TargetRole(role="DevOps Engineer", confidence=0.9)],
        skills=["Kubernetes", "Docker", "AWS"],
    )

    jobs = [
        JobPosting(
            id="job-devops",
            title="DevOps Engineer",
            company="CloudInc",
            location="Remote",
            remote=True,
            description="Seeking DevOps Engineer with K8s, Docker, and AWS experience.",
            apply_url="https://cloudinc.com/apply",
            source="Test",
        )
    ]

    ranked = await rank_and_enrich_jobs(jobs, profile, llm=None)
    assert len(ranked) == 1
    assert ranked[0].llm_score is None
    assert ranked[0].final_score == ranked[0].heuristic_score
    assert "Heuristic match" in ranked[0].match_reason


def test_jobs_search_sse_stream_endpoint(client: TestClient):
    """
    Verify POST /jobs/search streams SSE events: progress, source_status, and result.
    """
    search_payload = {
        "profile": {
            "target_roles": [{"role": "Software Engineer", "confidence": 0.9}],
            "skills": ["Python", "FastAPI"],
            "location": "Remote",
            "remote_preference": "remote",
            "experience_level": "mid",
            "years_experience": 4.0,
        },
        "sources": {
            "enable_remotive": True,
            "greenhouse_slugs": ["gitlab"],
        },
    }

    dummy_job = JobPosting(
        id="test-job-1",
        title="Software Engineer",
        company="GitLab",
        location="Remote",
        remote=True,
        description="FastAPI backend engineer.",
        apply_url="https://gitlab.com/apply",
        source="Greenhouse",
    )

    # Patch fetch_all_sources to return dummy job immediately
    with patch(
        "app.section4_ranking_and_search.routers.jobs.fetch_all_sources",
        new_callable=AsyncMock,
        return_value=[dummy_job],
    ):
        response = client.post(
            "/jobs/search",
            json=search_payload,
            headers={"X-LLM-Key": "gsk_dummy1234567890abcdef1234567890"},
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        body = response.text
        assert "event: progress" in body
        assert "preparing" in body
        assert "searching" in body
        assert "ranking" in body
        assert "complete" in body
        assert "event: result" in body
        assert "GitLab" in body
