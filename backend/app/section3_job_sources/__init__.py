"""
Section 3: Job Sources & Aggregation.
"""
from app.section3_job_sources.base import BaseSourceAdapter, strip_html
from app.section3_job_sources.cache import job_cache, AsyncJobCache
from app.section3_job_sources.registry import (
    SourceRegistry,
    fetch_all_sources,
    get_all_source_meta,
)

__all__ = [
    "BaseSourceAdapter",
    "strip_html",
    "job_cache",
    "AsyncJobCache",
    "SourceRegistry",
    "fetch_all_sources",
    "get_all_source_meta",
]
