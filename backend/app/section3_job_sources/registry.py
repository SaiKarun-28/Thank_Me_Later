"""
Job Sources Registry, metadata definitions, and concurrent aggregation pipeline.
Zero failures: One failing source never breaks the rest (asyncio.gather with return_exceptions=True).
"""
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from app.section1_foundation_and_providers.schemas.job import JobPosting, JobSourceConfig, SourceStatus
from app.section1_foundation_and_providers.schemas.settings import SourceFieldSchema, SourceMetaSchema
from app.section3_job_sources.adapters.adzuna import AdzunaAdapter
from app.section3_job_sources.adapters.ashby import AshbyAdapter
from app.section3_job_sources.adapters.greenhouse import GreenhouseAdapter
from app.section3_job_sources.adapters.jooble import JoobleAdapter
from app.section3_job_sources.adapters.jsearch import JSearchAdapter
from app.section3_job_sources.adapters.lever import LeverAdapter
from app.section3_job_sources.adapters.remotive import RemotiveAdapter
from app.section3_job_sources.base import BaseSourceAdapter

logger = logging.getLogger(__name__)

# Complete metadata for all 7 official/public job sources
SOURCE_METADATA: List[SourceMetaSchema] = [
    SourceMetaSchema(
        id="remotive",
        name="Remotive",
        is_keyless=True,
        attribution="Job data provided by Remotive",
        terms_url="https://remotive.com/legal",
        fields=[
            SourceFieldSchema(
                key="enable_remotive",
                label="Enable Remotive",
                type="select",
                required=False,
                default="true",
                options=["true", "false"],
                description="Search official public remote tech opportunities.",
            ),
        ],
    ),
    SourceMetaSchema(
        id="greenhouse",
        name="Greenhouse",
        is_keyless=True,
        fields=[
            SourceFieldSchema(
                key="greenhouse_slugs",
                label="Greenhouse Company Slugs",
                type="list",
                required=False,
                default=["gitlab", "cloudflare"],
                description="Comma-separated company slugs from greenhouse.io job boards.",
            ),
        ],
    ),
    SourceMetaSchema(
        id="lever",
        name="Lever",
        is_keyless=True,
        fields=[
            SourceFieldSchema(
                key="lever_slugs",
                label="Lever Company Slugs",
                type="list",
                required=False,
                default=["figma", "spotify"],
                description="Comma-separated company slugs from jobs.lever.co boards.",
            ),
        ],
    ),
    SourceMetaSchema(
        id="ashby",
        name="Ashby",
        is_keyless=True,
        fields=[
            SourceFieldSchema(
                key="ashby_slugs",
                label="Ashby Company Slugs",
                type="list",
                required=False,
                default=["ramp", "openai"],
                description="Comma-separated company slugs from jobs.ashbyhq.com boards.",
            ),
        ],
    ),
    SourceMetaSchema(
        id="jsearch",
        name="JSearch (RapidAPI)",
        is_keyless=False,
        fields=[
            SourceFieldSchema(
                key="jsearch_key",
                label="RapidAPI Key",
                type="password",
                required=False,
                description="RapidAPI key for the JSearch endpoint.",
            ),
        ],
    ),
    SourceMetaSchema(
        id="adzuna",
        name="Adzuna",
        is_keyless=False,
        fields=[
            SourceFieldSchema(
                key="adzuna_app_id",
                label="Adzuna App ID",
                type="text",
                required=False,
                description="Developer App ID from developer.adzuna.com.",
            ),
            SourceFieldSchema(
                key="adzuna_app_key",
                label="Adzuna App Key",
                type="password",
                required=False,
                description="Developer App Key from developer.adzuna.com.",
            ),
            SourceFieldSchema(
                key="adzuna_country",
                label="Country",
                type="select",
                required=False,
                default="us",
                options=["us", "in", "gb", "ca", "au", "de", "fr"],
                description="Target country code (including 'in' for India, 'us', 'gb').",
            ),
        ],
    ),
    SourceMetaSchema(
        id="jooble",
        name="Jooble",
        is_keyless=False,
        fields=[
            SourceFieldSchema(
                key="jooble_key",
                label="Jooble API Key",
                type="password",
                required=False,
                description="API key from jooble.org/api.",
            ),
        ],
    ),
]


def get_all_source_meta() -> List[SourceMetaSchema]:
    """Returns metadata schemas for all supported sources."""
    return SOURCE_METADATA


class SourceRegistry:
    @staticmethod
    def get_all_adapters() -> List[BaseSourceAdapter]:
        return [
            RemotiveAdapter(),
            GreenhouseAdapter(),
            LeverAdapter(),
            AshbyAdapter(),
            JSearchAdapter(),
            AdzunaAdapter(),
            JoobleAdapter(),
        ]


async def fetch_single_source(
    adapter: BaseSourceAdapter,
    queries: List[str],
    config: JobSourceConfig,
    on_status: Optional[Callable[[SourceStatus], Any]] = None,
) -> List[JobPosting]:
    """Runs a single adapter with isolated timeout and status callback."""
    if on_status:
        await on_status(SourceStatus(source_id=adapter.id, status="loading"))

    try:
        jobs = await asyncio.wait_for(
            adapter.fetch(queries, config),
            timeout=adapter.timeout,
        )
        if on_status:
            await on_status(SourceStatus(source_id=adapter.id, status="success", count=len(jobs)))
        return jobs
    except Exception as e:
        logger.warning("Source '%s' failed during fetch: %s", adapter.name, str(e))
        if on_status:
            await on_status(SourceStatus(source_id=adapter.id, status="error", message=str(e)))
        return []


async def fetch_all_sources(
    queries: List[str],
    config: JobSourceConfig,
    on_status: Optional[Callable[[SourceStatus], Any]] = None,
) -> List[JobPosting]:
    """
    Executes all 7 adapters concurrently with an isolated 10-second timeout per source.
    Uses asyncio.gather with return_exceptions=True so one source's failure never breaks the rest.
    """
    adapters = SourceRegistry.get_all_adapters()
    tasks = [fetch_single_source(adapter, queries, config, on_status=on_status) for adapter in adapters]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    aggregated: List[JobPosting] = []
    for idx, res in enumerate(results):
        if isinstance(res, list):
            aggregated.extend(res)
        elif isinstance(res, Exception):
            logger.error("Source adapter %s encountered unhandled exception: %s", adapters[idx].name, str(res))

    return aggregated
