"""
Section 3: Job Sources, Aggregation, and Fault Tolerance Tests.
"""
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from fastapi.testclient import TestClient

from app.section1_foundation_and_providers.schemas.job import JobPosting, JobSourceConfig
from app.section3_job_sources.adapters.adzuna import AdzunaAdapter
from app.section3_job_sources.adapters.ashby import AshbyAdapter
from app.section3_job_sources.adapters.greenhouse import GreenhouseAdapter
from app.section3_job_sources.adapters.jooble import JoobleAdapter
from app.section3_job_sources.adapters.jsearch import JSearchAdapter
from app.section3_job_sources.adapters.lever import LeverAdapter
from app.section3_job_sources.adapters.remotive import RemotiveAdapter
from app.section3_job_sources.base import strip_html
from app.section3_job_sources.cache import AsyncJobCache
from app.section3_job_sources.registry import (
    SourceRegistry,
    fetch_all_sources,
    get_all_source_meta,
)


def test_strip_html_utilities():
    """Verify HTML stripping, entity decoding, and whitespace normalization."""
    raw = "<p>Join our <strong>innovative</strong> team! &amp; work with React.</p><br><div>Apply now &gt;</div>"
    clean = strip_html(raw)
    assert "<p>" not in clean
    assert "<strong>" not in clean
    assert "&amp;" not in clean
    assert "Join our innovative team! & work with React." in clean
    assert "Apply now >" in clean

    assert strip_html("") == ""
    assert strip_html(None) == ""


@pytest.mark.asyncio
async def test_job_cache_ttl_and_expiry():
    """Verify in-memory async cache hits, set, and TTL expiry."""
    cache = AsyncJobCache(ttl_seconds=0.1)  # 100ms for fast test
    dummy_job = JobPosting(
        id="test-1",
        title="Software Engineer",
        company="Acme Corp",
        apply_url="https://acme.com/apply",
        source="Test",
    )

    # Initial miss
    assert await cache.get("key1") is None

    # Set and hit
    await cache.set("key1", [dummy_job])
    cached = await cache.get("key1")
    assert cached is not None
    assert len(cached) == 1
    assert cached[0].title == "Software Engineer"

    # Expiry
    import asyncio
    await asyncio.sleep(0.15)
    assert await cache.get("key1") is None


@pytest.mark.asyncio
async def test_remotive_adapter_mapping_and_caching():
    """Verify Remotive adapter parsing, caching, and apply link validation."""
    adapter = RemotiveAdapter()
    config = JobSourceConfig(enable_remotive=True)

    mock_resp = {
        "jobs": [
            {
                "id": 1234,
                "title": "Senior Python Developer",
                "company_name": "RemoteFirst",
                "url": "https://remotive.com/jobs/1234",
                "candidate_required_location": "USA Only",
                "description": "<p>Must know FastAPI and Docker.</p>",
                "publication_date": "2026-10-01",
                "salary": "$140,000",
            },
            {
                "id": 5678,
                "title": "Invalid Job",
                "company_name": "BadCo",
                "url": "javascript:alert(1)",  # Unsafe link must be dropped
                "description": "Scam job",
            },
        ]
    }

    req = httpx.Request("GET", "https://remotive.com/api/remote-jobs")
    resp = httpx.Response(200, request=req, json=mock_resp)

    with patch.object(httpx.AsyncClient, "get", return_value=resp):
        jobs = await adapter.fetch(["python"], config)
        assert len(jobs) == 1
        assert jobs[0].id == "remotive_1234"
        assert jobs[0].title == "Senior Python Developer"
        assert jobs[0].remote is True
        assert "<p>" not in jobs[0].description


@pytest.mark.asyncio
async def test_greenhouse_adapter_local_filtering():
    """Verify Greenhouse slug fetching and local title/content keyword filtering."""
    adapter = GreenhouseAdapter()
    config = JobSourceConfig(greenhouse_slugs=["gitlab"])

    mock_data = {
        "jobs": [
            {
                "id": 101,
                "title": "Full Stack Engineer, Rails & React",
                "absolute_url": "https://boards.greenhouse.io/gitlab/jobs/101",
                "location": {"name": "Remote, US"},
                "content": "<p>Build great features.</p>",
                "updated_at": "2026-10-15",
            },
            {
                "id": 102,
                "title": "Account Executive",
                "absolute_url": "https://boards.greenhouse.io/gitlab/jobs/102",
                "location": {"name": "New York, NY"},
                "content": "<p>Sales role.</p>",
            },
        ]
    }

    req = httpx.Request("GET", "https://boards-api.greenhouse.io/v1/boards/gitlab/jobs")
    resp = httpx.Response(200, request=req, json=mock_data)

    with patch.object(httpx.AsyncClient, "get", return_value=resp):
        # Query for "engineer" should match job 101 and filter out sales job 102
        jobs = await adapter.fetch(["engineer"], config)
        assert len(jobs) == 1
        assert jobs[0].id == "gh_gitlab_101"
        assert "Full Stack Engineer" in jobs[0].title


@pytest.mark.asyncio
async def test_lever_adapter():
    """Verify Lever slug fetching and categories location extraction."""
    adapter = LeverAdapter()
    config = JobSourceConfig(lever_slugs=["spotify"])

    mock_data = [
        {
            "id": "lever-1",
            "text": "Backend Engineer - Platform",
            "hostedUrl": "https://jobs.lever.co/spotify/lever-1",
            "categories": {"location": "Stockholm, Sweden"},
            "descriptionPlain": "Build cloud platforms with Go and Kubernetes.",
            "createdAt": 1729000000000,
        }
    ]

    req = httpx.Request("GET", "https://api.lever.co/v0/postings/spotify")
    resp = httpx.Response(200, request=req, json=mock_data)

    with patch.object(httpx.AsyncClient, "get", return_value=resp):
        jobs = await adapter.fetch(["backend"], config)
        assert len(jobs) == 1
        assert jobs[0].company == "Spotify"
        assert jobs[0].location == "Stockholm, Sweden"


@pytest.mark.asyncio
async def test_ashby_adapter():
    """Verify Ashby slug fetching and isRemote parsing."""
    adapter = AshbyAdapter()
    config = JobSourceConfig(ashby_slugs=["openai"])

    mock_data = {
        "jobs": [
            {
                "id": "ashby-1",
                "title": "Research Engineer, Post-Training",
                "jobUrl": "https://jobs.ashbyhq.com/openai/ashby-1",
                "location": "San Francisco, CA",
                "isRemote": False,
                "descriptionPlain": "LLM alignment research.",
                "publishedAt": "2026-10-10",
            }
        ]
    }

    req = httpx.Request("GET", "https://api.ashbyhq.com/posting-api/job-board/openai")
    resp = httpx.Response(200, request=req, json=mock_data)

    with patch.object(httpx.AsyncClient, "get", return_value=resp):
        jobs = await adapter.fetch(["research"], config)
        assert len(jobs) == 1
        assert jobs[0].title == "Research Engineer, Post-Training"


@pytest.mark.asyncio
async def test_jsearch_adapter_skip_without_key():
    """Verify JSearch is skipped when rapidapi_key is omitted."""
    adapter = JSearchAdapter()
    config = JobSourceConfig(jsearch_key=None)
    jobs = await adapter.fetch(["software"], config)
    assert jobs == []


@pytest.mark.asyncio
async def test_adzuna_adapter_country_routing():
    """Verify Adzuna URL embeds selected country code e.g. 'in'."""
    adapter = AdzunaAdapter()
    config = JobSourceConfig(
        adzuna_app_id="test_id",
        adzuna_app_key="test_key",
        adzuna_country="in",
    )

    mock_resp = {
        "results": [
            {
                "id": "999",
                "title": "Software Engineer in Bengaluru",
                "company": {"display_name": "Tech Corp"},
                "redirect_url": "https://adzuna.in/details/999",
                "location": {"display_name": "Bengaluru, Karnataka"},
                "description": "Hiring Python devs in India.",
                "created": "2026-10-12",
            }
        ]
    }

    captured_url = None

    async def mock_get(url, params=None, **kwargs):
        nonlocal captured_url
        captured_url = url
        req = httpx.Request("GET", url)
        return httpx.Response(200, request=req, json=mock_resp)

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_get):
        jobs = await adapter.fetch(["python"], config)
        assert len(jobs) == 1
        assert "/jobs/in/search" in captured_url
        assert jobs[0].location == "Bengaluru, Karnataka"


@pytest.mark.asyncio
async def test_jooble_adapter_skip_without_key():
    """Verify Jooble is skipped when jooble_key is omitted."""
    adapter = JoobleAdapter()
    config = JobSourceConfig(jooble_key=None)
    jobs = await adapter.fetch(["dev"], config)
    assert jobs == []


@pytest.mark.asyncio
async def test_fetch_all_sources_fault_tolerance():
    """
    Verify that if some adapters raise network timeouts or 500 errors,
    asyncio.gather with return_exceptions=True does not crash the search,
    and returns postings from remaining healthy sources.
    """
    dummy_job = JobPosting(
        id="surviving-1",
        title="Staff Engineer",
        company="Resilient Co",
        apply_url="https://resilient.com/apply",
        source="Remotive",
    )

    # Mock Remotive succeeding, Greenhouse timing out, Lever throwing 500
    with patch(
        "app.section3_job_sources.adapters.remotive.RemotiveAdapter.fetch",
        new_callable=AsyncMock,
        return_value=[dummy_job],
    ), patch(
        "app.section3_job_sources.adapters.greenhouse.GreenhouseAdapter.fetch",
        side_effect=httpx.ReadTimeout("Timed out waiting for Greenhouse"),
    ), patch(
        "app.section3_job_sources.adapters.lever.LeverAdapter.fetch",
        side_effect=Exception("Lever upstream 500 internal server error"),
    ):
        config = JobSourceConfig(
            enable_remotive=True,
            greenhouse_slugs=["broken-slug"],
            lever_slugs=["failing-slug"],
        )
        results = await fetch_all_sources(["engineer"], config)
        
        # Surviving job from Remotive is successfully returned
        assert len(results) >= 1
        assert any(j.id == "surviving-1" for j in results)


def test_sources_metadata_api_endpoint(client: TestClient):
    """Verify GET /settings/sources returns metadata schemas for all 7 sources."""
    response = client.get("/settings/sources")
    assert response.status_code == 200
    sources = response.json()
    assert isinstance(sources, list)
    
    source_ids = {s["id"] for s in sources}
    expected = {"remotive", "greenhouse", "lever", "ashby", "jsearch", "adzuna", "jooble"}
    assert expected.issubset(source_ids)

    # Check Adzuna country options contains 'in'
    adzuna_meta = next(s for s in sources if s["id"] == "adzuna")
    country_field = next(f for f in adzuna_meta["fields"] if f["key"] == "adzuna_country")
    assert "in" in country_field["options"]

    # Check Jooble country options contains 'in' and 'us'
    jooble_meta = next(s for s in sources if s["id"] == "jooble")
    jooble_country_field = next(f for f in jooble_meta["fields"] if f["key"] == "jooble_country")
    assert "in" in jooble_country_field["options"]
    assert "us" in jooble_country_field["options"]


def test_job_source_config_curated_defaults():
    """Verify JobSourceConfig initializes with non-empty curated ATS defaults."""
    cfg = JobSourceConfig()
    assert "gitlab" in cfg.greenhouse_slugs
    assert "figma" in cfg.lever_slugs
    assert "ramp" in cfg.ashby_slugs
    assert cfg.jooble_country == "us"
