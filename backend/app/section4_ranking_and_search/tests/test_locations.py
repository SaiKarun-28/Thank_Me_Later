import pytest
from app.section1_foundation_and_providers.schemas.job import JobLocation, JobPosting
from app.section4_ranking_and_search.services.locations import (
    normalize_raw_location,
    is_location_eligible,
    classify_seniority,
    freshness_classification,
)

def test_normalize_raw_location():
    loc = normalize_raw_location("Hyderabad, Telangana, India")
    assert loc.city == "Hyderabad"
    assert loc.state == "Telangana"
    assert loc.country == "India"
    assert loc.country_code == "IN"

    loc_remote = normalize_raw_location("Remote")
    assert loc_remote.is_remote is True

def test_is_location_eligible():
    selected = JobLocation(city="Hyderabad", state="Telangana", country="India", country_code="IN")

    # Matching
    job_match = JobPosting(id="1", title="Dev", company="A", apply_url="http://a.com", location="Hyderabad, Telangana, India")
    assert is_location_eligible(job_match, selected) is True

    # Mismatch
    job_mismatch = JobPosting(id="2", title="Dev", company="B", apply_url="http://b.com", location="Bengaluru, Karnataka, India")
    assert is_location_eligible(job_mismatch, selected) is False

def test_classify_seniority():
    assert classify_seniority(0.2) == "internship"
    assert classify_seniority(4.0) == "mid-level"
    assert classify_seniority(25.0) == "director"

def test_freshness_classification():
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)

    recent = (now - timedelta(days=2)).isoformat()
    assert freshness_classification(recent)[0] == "published_within_7d"

    old = (now - timedelta(days=40)).isoformat()
    assert freshness_classification(old)[0] == "older_than_30d"
