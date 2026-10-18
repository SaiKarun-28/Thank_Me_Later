"""
JSearch (RapidAPI) Source Adapter.
Official REST API query-based aggregator.
"""
import logging
from typing import List
import httpx

from app.section1_foundation_and_providers.schemas.job import JobPosting, JobSourceConfig
from app.section1_foundation_and_providers.security.security import register_secret
from app.section3_job_sources.base import BaseSourceAdapter

logger = logging.getLogger(__name__)


class JSearchAdapter(BaseSourceAdapter):
    """
    Adapter for JSearch via RapidAPI.
    """
    def __init__(self):
        super().__init__(
            id="jsearch",
            name="JSearch",
            is_keyless=False,
            timeout=10.0,
        )

    async def fetch(self, queries: List[str], config: JobSourceConfig) -> List[JobPosting]:
        if not config.jsearch_key:
            logger.debug("JSearch key not supplied; skipping JSearch source.")
            return []

        register_secret(config.jsearch_key)
        all_postings: List[JobPosting] = []
        primary_query = queries[0] if queries else "software engineer"

        headers = {
            "X-RapidAPI-Key": config.jsearch_key.strip(),
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            "User-Agent": "ThankMeLater/0.1.0",
        }
        params = {
            "query": primary_query,
            "page": "1",
            "num_pages": "1",
            "date_posted": "month",
        }

        url = "https://jsearch.p.rapidapi.com/search"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
                raw_jobs = data.get("data", [])

                for item in raw_jobs:
                    city = item.get("job_city") or ""
                    state = item.get("job_state") or ""
                    country = item.get("job_country") or ""
                    loc_parts = [p for p in (city, state, country) if p]
                    loc = ", ".join(loc_parts)

                    salary_str = None
                    if item.get("job_min_salary"):
                        salary_str = f"{item.get('job_min_salary')}-{item.get('job_max_salary')} {item.get('job_salary_currency', 'USD')}"

                    posting = self.build_posting(
                        id=f"jsearch_{item.get('job_id')}",
                        title=item.get("job_title", ""),
                        company=item.get("employer_name", ""),
                        apply_url=item.get("job_apply_link", ""),
                        location=loc,
                        remote=bool(item.get("job_is_remote", False)),
                        description=item.get("job_description", ""),
                        posted_date=item.get("job_posted_at_datetime_utc"),
                        salary=salary_str,
                    )
                    if posting:
                        all_postings.append(posting)
        except Exception as e:
            logger.warning("JSearch fetch error: %s", str(e))

        return all_postings
