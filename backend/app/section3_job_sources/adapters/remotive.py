"""
Remotive Source Adapter (Official Public Remote Jobs API).
Keyless with 10-minute in-memory cache and Remotive attribution.
"""
import logging
from typing import List
import httpx

from app.section1_foundation_and_providers.schemas.job import JobPosting, JobSourceConfig
from app.section3_job_sources.base import BaseSourceAdapter
from app.section3_job_sources.cache import job_cache

logger = logging.getLogger(__name__)


class RemotiveAdapter(BaseSourceAdapter):
    """
    Fetches remote opportunities from Remotive's public API.
    """
    def __init__(self):
        super().__init__(
            id="remotive",
            name="Remotive",
            is_keyless=True,
            timeout=10.0,
        )

    async def fetch(self, queries: List[str], config: JobSourceConfig) -> List[JobPosting]:
        if not config.enable_remotive:
            return []

        all_postings: List[JobPosting] = []
        # Query using the primary high-intent search query
        primary_query = queries[0] if queries else "software"
        cache_key = f"remotive:{primary_query.lower().strip()}"

        # 1. Check in-memory 10-min cache
        cached = await job_cache.get(cache_key)
        if cached is not None:
            logger.debug("Remotive cache hit for query: %s", primary_query)
            return cached

        url = f"https://remotive.com/api/remote-jobs?search={primary_query}&limit=50"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers={"User-Agent": "ThankMeLater/0.1.0"})
                resp.raise_for_status()
                data = resp.json()
                raw_jobs = data.get("jobs", [])

                for item in raw_jobs:
                    posting = self.build_posting(
                        id=f"remotive_{item.get('id')}",
                        title=item.get("title", ""),
                        company=item.get("company_name", ""),
                        apply_url=item.get("url", ""),
                        location=item.get("candidate_required_location") or "Remote",
                        remote=True,
                        description=item.get("description", ""),
                        posted_date=item.get("publication_date"),
                        salary=item.get("salary"),
                    )
                    if posting:
                        all_postings.append(posting)

            # Store in cache
            await job_cache.set(cache_key, all_postings)
        except Exception as e:
            logger.warning("Remotive fetch error: %s", str(e))

        return all_postings
