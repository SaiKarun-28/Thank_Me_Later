"""
Adzuna Source Adapter.
Official REST API job index with international country routing (including India "in").
"""
import logging
from typing import List
import httpx

from app.section1_foundation_and_providers.schemas.job import JobPosting, JobSourceConfig
from app.section1_foundation_and_providers.security.security import register_secret
from app.section3_job_sources.base import BaseSourceAdapter

logger = logging.getLogger(__name__)


class AdzunaAdapter(BaseSourceAdapter):
    """
    Adapter for Adzuna REST API.
    """
    def __init__(self):
        super().__init__(
            id="adzuna",
            name="Adzuna",
            is_keyless=False,
            timeout=10.0,
        )

    async def fetch(self, queries: List[str], config: JobSourceConfig) -> List[JobPosting]:
        if not config.adzuna_app_id or not config.adzuna_app_key:
            logger.debug("Adzuna app_id or app_key not supplied; skipping Adzuna source.")
            return []

        register_secret(config.adzuna_app_key)
        all_postings: List[JobPosting] = []
        primary_query = queries[0] if queries else "developer"
        country = (config.adzuna_country or "us").lower().strip()

        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": config.adzuna_app_id.strip(),
            "app_key": config.adzuna_app_key.strip(),
            "what": primary_query,
            "results_per_page": 20,
            "max_days_old": 30,
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params, headers={"User-Agent": "ThankMeLater/0.1.0"})
                resp.raise_for_status()
                data = resp.json()
                raw_results = data.get("results", [])

                for item in raw_results:
                    company_name = ""
                    if isinstance(item.get("company"), dict):
                        company_name = item["company"].get("display_name", "")

                    loc_name = ""
                    if isinstance(item.get("location"), dict):
                        loc_name = item["location"].get("display_name", "")

                    salary_str = None
                    if item.get("salary_min"):
                        salary_str = f"{item.get('salary_min')}-{item.get('salary_max')}"

                    posting = self.build_posting(
                        id=f"adzuna_{item.get('id')}",
                        title=item.get("title", ""),
                        company=company_name,
                        apply_url=item.get("redirect_url", ""),
                        location=loc_name,
                        description=item.get("description", ""),
                        posted_date=item.get("created"),
                        salary=salary_str,
                    )
                    if posting:
                        all_postings.append(posting)
        except Exception as e:
            logger.warning("Adzuna fetch error: %s", str(e))

        return all_postings
