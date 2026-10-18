"""
Job source adapters.
"""
from app.section3_job_sources.adapters.remotive import RemotiveAdapter
from app.section3_job_sources.adapters.greenhouse import GreenhouseAdapter
from app.section3_job_sources.adapters.lever import LeverAdapter
from app.section3_job_sources.adapters.ashby import AshbyAdapter
from app.section3_job_sources.adapters.jsearch import JSearchAdapter
from app.section3_job_sources.adapters.adzuna import AdzunaAdapter
from app.section3_job_sources.adapters.jooble import JoobleAdapter

__all__ = [
    "RemotiveAdapter",
    "GreenhouseAdapter",
    "LeverAdapter",
    "AshbyAdapter",
    "JSearchAdapter",
    "AdzunaAdapter",
    "JoobleAdapter",
]
