"""
Job and Ranking Data Models.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from app.schemas.resume import SearchProfile


class JobPosting(BaseModel):
    """Normalized raw job posting from any source."""
    id: str
    title: str
    company: str
    location: str = ""
    remote: bool = False
    description: str = ""
    apply_url: str
    posted_date: Optional[str] = None
    source: str
    salary: Optional[str] = None


class RankedJob(JobPosting):
    """Job enriched with match calculations."""
    heuristic_score: float = Field(ge=0.0, le=100.0)
    llm_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    final_score: float = Field(ge=0.0, le=100.0)
    match_reason: str = ""
    required_skills: List[str] = Field(default_factory=list)
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)


class SourceStatus(BaseModel):
    """Status update for an external source emitted over SSE."""
    source_id: str
    status: Literal["pending", "loading", "success", "error"]
    count: int = 0
    message: Optional[str] = None


class JobSourceConfig(BaseModel):
    """User-supplied credentials & slugs for official/public job sources."""
    # JSearch (RapidAPI)
    jsearch_key: Optional[str] = None

    # Adzuna
    adzuna_app_id: Optional[str] = None
    adzuna_app_key: Optional[str] = None
    adzuna_country: str = "us"

    # Jooble
    jooble_key: Optional[str] = None

    # Company ATS slugs (Keyless)
    greenhouse_slugs: List[str] = Field(default_factory=list)
    lever_slugs: List[str] = Field(default_factory=list)
    ashby_slugs: List[str] = Field(default_factory=list)

    # Remotive (Keyless)
    enable_remotive: bool = True


class SearchJobsRequest(BaseModel):
    """Payload for POST /jobs/search."""
    profile: SearchProfile
    sources: JobSourceConfig = Field(default_factory=JobSourceConfig)
