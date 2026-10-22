"""
Greenhouse Source Adapter (Keyless Company Board API).
Fetches jobs from company slugs and filters locally by role query keywords.
"""
import logging
from typing import List
import httpx

from app.section1_foundation_and_providers.schemas.job import JobPosting, JobSourceConfig
from app.section3_job_sources.base import BaseSourceAdapter
from app.section3_job_sources.cache import job_cache

logger = logging.getLogger(__name__)


class GreenhouseAdapter(BaseSourceAdapter):
    """
    Adapter for public Greenhouse company job boards (e.g. /v1/boards/{slug}/jobs).
    """
    def __init__(self):
        super().__init__(
            id="greenhouse",
            name="Greenhouse",
            is_keyless=True,
            timeout=10.0,
        )

    async def fetch(self, queries: List[str], config: JobSourceConfig) -> List[JobPosting]:
        slugs = [s.strip().lower() for s in config.greenhouse_slugs if s.strip()]
        if not slugs:
            return []

        all_postings: List[JobPosting] = []
        keywords = set()
        for q in queries:
            for token in q.lower().split():
                if len(token) > 2:
                    keywords.add(token)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for slug in slugs:
                cache_key = f"greenhouse:{slug}"
                cached = await job_cache.get(cache_key)

                raw_jobs = None
                if cached is not None:
                    raw_jobs = cached
                else:
                    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
                    try:
                        resp = await client.get(url, headers={"User-Agent": "ThankMeLater/0.1.0"})
                        if resp.status_code == 200:
                            data = resp.json()
                            board_jobs = data.get("jobs", [])
                            company_postings = []
                            for item in board_jobs:
                                posting = self.build_posting(
                                    id=f"gh_{slug}_{item.get('id')}",
                                    title=item.get("title", ""),
                                    company=item.get("company_name") or slug.capitalize(),
                                    apply_url=item.get("absolute_url", ""),
                                    location=item.get("location", {}).get("name", "") if isinstance(item.get("location"), dict) else "",
                                    description=item.get("content", ""),
                                    posted_date=item.get("updated_at"),
                                )
                                if posting:
                                    company_postings.append(posting)
                            await job_cache.set(cache_key, company_postings)
                            raw_jobs = company_postings
                    except Exception as e:
                        logger.warning("Error fetching Greenhouse slug '%s': %s", slug, str(e))
                        continue

                # Local keyword matching
                if raw_jobs:
                    for job in raw_jobs:
                        title_lower = job.title.lower()
                        # If any keyword matches or no queries specified, include job
                        if not keywords or any(kw in title_lower for kw in keywords):
                            all_postings.append(job)

        return all_postings
