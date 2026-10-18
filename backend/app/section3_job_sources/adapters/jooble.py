"""
Jooble Source Adapter.
Official REST API job aggregator via JSON POST.
"""
import logging
from typing import List
import httpx

from app.section1_foundation_and_providers.schemas.job import JobPosting, JobSourceConfig
from app.section1_foundation_and_providers.security.security import register_secret
from app.section3_job_sources.base import BaseSourceAdapter

logger = logging.getLogger(__name__)


class JoobleAdapter(BaseSourceAdapter):
    """
    Adapter for Jooble API.
    """
    def __init__(self):
        super().__init__(
            id="jooble",
            name="Jooble",
            is_keyless=False,
            timeout=10.0,
        )

    async def fetch(self, queries: List[str], config: JobSourceConfig) -> List[JobPosting]:
        if not config.jooble_key:
            logger.debug("Jooble key not supplied; skipping Jooble source.")
            return []

        register_secret(config.jooble_key)
        all_postings: List[JobPosting] = []
        primary_query = queries[0] if queries else "software engineer"

        url = f"https://jooble.org/api/{config.jooble_key.strip()}"
        payload = {
            "keywords": primary_query,
            "page": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers={"User-Agent": "ThankMeLater/0.1.0"})
                resp.raise_for_status()
                data = resp.json()
                raw_jobs = data.get("jobs", [])

                for item in raw_jobs:
                    posting = self.build_posting(
                        id=f"jooble_{item.get('id')}",
                        title=item.get("title", ""),
                        company=item.get("company", ""),
                        apply_url=item.get("link", ""),
                        location=item.get("location", ""),
                        description=item.get("snippet", ""),
                        posted_date=item.get("updated"),
                        salary=item.get("salary"),
                    )
                    if posting:
                        all_postings.append(posting)
        except Exception as e:
            logger.warning("Jooble fetch error: %s", str(e))

        return all_postings
