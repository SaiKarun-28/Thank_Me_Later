"""
Lever Source Adapter (Keyless Company Board API).
Fetches postings from company slugs and filters locally by role query keywords.
"""
import logging
from typing import List
import httpx

from app.section1_foundation_and_providers.schemas.job import JobPosting, JobSourceConfig
from app.section3_job_sources.base import BaseSourceAdapter
from app.section3_job_sources.cache import job_cache

logger = logging.getLogger(__name__)


class LeverAdapter(BaseSourceAdapter):
    """
    Adapter for public Lever company job boards (e.g. /v0/postings/{slug}?mode=json).
    """
    def __init__(self):
        super().__init__(
            id="lever",
            name="Lever",
            is_keyless=True,
            timeout=10.0,
        )

    async def fetch(self, queries: List[str], config: JobSourceConfig) -> List[JobPosting]:
        slugs = [s.strip().lower() for s in config.lever_slugs if s.strip()]
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
                cache_key = f"lever:{slug}"
                cached = await job_cache.get(cache_key)

                raw_jobs = None
                if cached is not None:
                    raw_jobs = cached
                else:
                    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
                    try:
                        resp = await client.get(url, headers={"User-Agent": "ThankMeLater/0.1.0"})
                        if resp.status_code == 200:
                            postings_data = resp.json()
                            if not isinstance(postings_data, list):
                                postings_data = []
                            company_postings = []
                            for item in postings_data:
                                categories = item.get("categories", {}) if isinstance(item.get("categories"), dict) else {}
                                location = categories.get("location", "")
                                apply_url = item.get("hostedUrl") or item.get("applyUrl") or ""
                                desc = item.get("descriptionPlain") or item.get("description") or ""

                                posting = self.build_posting(
                                    id=f"lever_{slug}_{item.get('id')}",
                                    title=item.get("text", ""),
                                    company=slug.capitalize(),
                                    apply_url=apply_url,
                                    location=location,
                                    description=desc,
                                    posted_date=str(item.get("createdAt")) if item.get("createdAt") else None,
                                )
                                if posting:
                                    company_postings.append(posting)
                            await job_cache.set(cache_key, company_postings)
                            raw_jobs = company_postings
                    except Exception as e:
                        logger.warning("Error fetching Lever slug '%s': %s", slug, str(e))
                        continue

                # Local keyword matching
                if raw_jobs:
                    for job in raw_jobs:
                        title_lower = job.title.lower()
                        if not keywords or any(kw in title_lower for kw in keywords):
                            all_postings.append(job)

        return all_postings
