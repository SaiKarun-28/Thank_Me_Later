"""
Location, seniority & freshness utilities — shared across ranking & adapters.
Zero external deps; stdlib-only. Uses normalized JobLocation / SearchProfile shapes.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional, Tuple

from app.section1_foundation_and_providers.schemas.job import JobLocation, JobPosting
from app.section1_foundation_and_providers.schemas.resume import SearchProfile


def normalize_raw_location(raw: str) -> JobLocation:
    """
    Parse a free-form location string into a structured JobLocation.
    Supports forms like:
      "Hyderabad, Telangana, India"
      "Hyderabad, India"
      "Remote"
      "Bengaluru, Karnataka"
    Returns a JobLocation with coordinates from a best-effort parse;
    if the provider cannot supply coordinates, they remain 0.0.
    """
    raw_lower = raw.strip().lower()
    loc = JobLocation(city="", state="", country="", country_code="", latitude=0.0, longitude=0.0)

    # Quick remote detection
    if raw_lower in {"remote", "any", "remote only", "work from anywhere"}:
        loc.is_remote = True
        return loc

    # Very simple token-based split on commas: city, state?, country?
    parts = [p.strip() for p in raw.split(",")]
    if not parts:
        return loc

    # City is first token (or first two tokens if only 2 parts and looks like city,state)
    city_part = parts[0]
    loc.city = _title_case(city_part)

    if len(parts) >= 2:
        # Second token could be state or country
        second = parts[1]
        # If second looks like a 2-letter country code or known country name
        if re.fullmatch(r"[A-Za-z]{2}", second) or second in {"uk", "us", "in", "gb", "ca", "au", "de", "fr"}:
            loc.country = _title_case(second)
            loc.country_code = second.upper()
        else:
            loc.state = _title_case(second)

    if len(parts) >= 3:
        # Third token is country
        loc.country = _title_case(parts[2])
        loc.country_code = _country_code_from_name(parts[2]) or ""

    # If we have city+state+country, derive country_code
    if not loc.country_code and loc.city and loc.state:
        # fallback: try to infer
        pass

    # Normalise is_remote/onsite/hybrid from the string if present
    if "remote" in raw_lower and not loc.is_remote:
        # if no explicit city/state/country, treat as remote-only
        if not loc.city and not loc.state and not loc.country:
            loc.is_remote = True

    return loc


def _title_case(s: str) -> str:
    return s[0].upper() + s[1:].lower() if s else ""


def _country_code_from_name(name: str) -> Optional[str]:
    map_ = {
        "india": "IN",
        "united states": "US",
        "usa": "US",
        "u.s.": "US",
        "united kingdom": "GB",
        "uk": "GB",
        "great britain": "GB",
        "canada": "CA",
        "australia": "AU",
        "germany": "DE",
        "france": "FR",
    }
    return map_.get(name.lower())


def is_location_eligible(
    job: JobPosting,
    selected: JobLocation,
    remote_preference: str = "any",
    strict: bool = True,
) -> bool:
    """
    Location eligibility check.
    If strict=True: exact match required (city/state/country).
    If strict=False: nearby match allowed (state/country only).
    """
    # Remote jobs
    if job.remote or (job.location and "remote" in job.location.lower()):
        return remote_preference in {"remote", "hybrid", "any"}

    # Job has no location info
    if not job.location_data and not job.location:
        return False

    # Normalise job location
    job_loc = job.location_data or normalize_raw_location(job.location or "")

    # Match country and state
    country_match = (
        selected.country_code and job_loc.country_code and
        selected.country_code.lower() == job_loc.country_code.lower()
    )
    state_match = (
        selected.state and job_loc.state and
        selected.state.lower() == job_loc.state.lower()
    )
    city_match = (
        selected.city and job_loc.city and
        selected.city.lower() == job_loc.city.lower()
    )

    if strict:
        # Require exact city match (if city provided)
        if selected.city:
            return city_match and (state_match or country_match)
        return state_match or country_match
    else:
        # Nearby match: state/country match, city doesn't have to match (or exist)
        return state_match or country_match


def is_nearby_location(job: JobPosting, selected: JobLocation) -> bool:
    """
    Check if a job is nearby based on state and country match (excluding city match).
    """
    # Get normalized job location
    job_loc = job.location_data or normalize_raw_location(job.location or "")

    # Check state match
    state_match = (
        selected.state and job_loc.state and
        selected.state.lower() == job_loc.state.lower()
    )

    # Check country match
    country_match = (
        selected.country_code and job_loc.country_code and
        selected.country_code.lower() == job_loc.country_code.lower()
    )

    # Nearby means state and country match (city may differ)
    return state_match and country_match


def classify_seniority(years: float) -> str:
    """
    Map verified years of experience to a standard seniority band.
    - Internship: < 0.5
    - Fresher: < 1.0
    - Junior: < 3.0
    - Mid-level: < 6.0
    - Senior: < 10.0
    - Lead: < 15.0
    - Manager: < 20.0
    - Director: >= 20.0 (or unknown)
    """
    if years < 0.5:
        return "internship"
    if years < 1.0:
        return "fresher"
    if years < 3.0:
        return "junior"
    if years < 6.0:
        return "mid-level"
    if years < 10.0:
        return "senior"
    if years < 15.0:
        return "lead"
    if years < 20.0:
        return "manager"
    return "director"


def freshness_classification(posted_date: Optional[str]) -> Tuple[str, int]:
    """
    Classify a job's publication date.

    Returns (bucket, score) where:
    - "published_within_7d": score 10
    - "published_within_30d": score 5
    - "older_than_30d": score 0
    - "unknown_date": score 0 (never award freshness for unknown)
    - "future_date": score 0 (exclude)
    """
    if not posted_date:
        return "unknown_date", 0

    now = datetime.now(timezone.utc)
    try:
        date_str = str(posted_date).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(date_str)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        # Future dates
        if parsed > now:
            return "future_date", 0
        days = (now - parsed).total_seconds() / 86400.0
        if days <= 7.0:
            return "published_within_7d", 10
        if days <= 30.0:
            return "published_within_30d", 5
        return "older_than_30d", 0
    except Exception:
        # Unparseable date — never treat as recent
        return "unknown_date", 0


SENIORITY_MAP = {
    "intern": ["intern", "internship"],
    "fresher": ["fresher", "entry level", "graduate"],
    "junior": ["junior", "jr."],
    "mid": ["mid", "mid-level", "developer", "engineer"],
    "senior": ["senior", "sr.", "lead"],
    "lead": ["staff", "principal", "lead"],
    "manager": ["manager", "head of", "director of"],
    "director": ["director", "vp", "vice president", "cto", "cfo"]
}

def classify_job_seniority(job_title: str) -> str:
    """Classifies job title into a seniority level."""
    title_lower = job_title.lower()
    for level, keywords in SENIORITY_MAP.items():
        if any(k in title_lower for k in keywords):
            return level
    return "mid"

def calculate_seniority_compatibility(candidate_level: str, job_level: str) -> float:
    """Returns compatibility score (0-100) between candidate and job seniority."""
    levels = ["intern", "fresher", "junior", "mid", "senior", "lead", "manager", "director"]
    try:
        cand_idx = levels.index(candidate_level.lower())
        job_idx = levels.index(job_level)
    except ValueError:
        return 50.0

    diff = job_idx - cand_idx
    if diff == 0:
        return 100.0
    if diff == 1:
        return 80.0
    if diff == -1:
        return 60.0
    if diff > 1:
        return 30.0  # Underqualified
    return 20.0  # Overqualified

def calculate_fit_score(profile: SearchProfile, job: JobPosting) -> float:
    """Calculates remote/location and seniority fit (0-100)."""
    score = 70.0  # Default baseline

    # Remote preference matching
    pref = profile.remote_preference.lower()
    if pref == "remote":
        if job.remote or "remote" in job.location.lower():
            score += 15.0
        else:
            score -= 10.0
    elif pref in ("onsite", "hybrid", "local"):
        if profile.location and profile.location.lower() in job.location.lower():
            score += 15.0

    # Seniority compatibility
    job_level = classify_job_seniority(job.title)
    seniority_score = calculate_seniority_compatibility(profile.experience_level, job_level)

    # Weight: 60% Seniority, 40% Remote/Location baseline
    total_score = (0.6 * seniority_score) + (0.4 * score)

    return max(0.0, min(100.0, total_score))