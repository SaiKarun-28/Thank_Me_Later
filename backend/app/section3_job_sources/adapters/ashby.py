"""
Ashby Source Adapter (Keyless Company Board API).
Fetches postings from company slugs and filters locally by role query keywords.
"""
import logging
from typing import List
import httpx

from app.section1_foundation_and_providers.schemas.job import JobPosting, JobSourceConfig
from app.section3_job_sources.base import BaseSourceAdapter
from app.section3_job_sources.cache import job_cache

logger = logging.getLogger(__name__)


class AshbyAdapter(BaseSourceAdapter):
    """
    Adapter for public Ashby company job boards (e.g. /posting-api/job-board/{slug}).
    """
    def __init__(self):
        super().__init__(
            id="ashby",
            name="Ashby",
            is_keyless=True,
            timeout=10.0,
        )

    async def fetch(self, queries: List[str], config: JobSourceConfig) -> List[JobPosting]:
        slugs = [s.strip().lower() for s in config.ashby_slugs if s.strip()]
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
                cache_key = f"ashby:{slug}"
                cached = await job_cache.get(cache_key)

                raw_jobs = None
                if cached is not None:
                    raw_jobs = cached
                else:
                    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
                    try:
                        resp = await client.get(url, headers={"User-Agent": "ThankMeLater/0.1.0"})
                        if resp.status_code == 200:
                            data = resp.json()
                            board_jobs = data.get("jobs", [])
                            company_postings = []
                            for item in board_jobs:
                                apply_url = item.get("jobUrl") or item.get("applyUrl") or ""
                                desc = item.get("descriptionHtml") or item.get("descriptionPlain") or ""
                                is_remote = item.get("isRemote", False) or "remote" in (item.get("location") or "").lower()

                                posting = self.build_posting(
                                    id=f"ashby_{slug}_{item.get('id')}",
                                    title=item.get("title", ""),
                                    company=slug.capitalize(),
                                    apply_url=apply_url,
                                    location=item.get("location", ""),
                                    remote=is_remote,
                                    description=desc,
                                    posted_date=item.get("publishedAt"),
                                )
                                if posting:
                                    company_postings.append(posting)
                            await job_cache.set(cache_key, company_postings)
                            raw_jobs = company_postings
                    except Exception as e:
                        logger.warning("Error fetching Ashby slug '%s': %s", slug, str(e))
                        continue

                # Local keyword matching
                if raw_jobs:
                    for job in raw_jobs:
                        title_lower = job.title.lower()
                        if not keywords or any(kw in title_lower for kw in keywords):
                            all_postings.append(job)

        return all_postings
