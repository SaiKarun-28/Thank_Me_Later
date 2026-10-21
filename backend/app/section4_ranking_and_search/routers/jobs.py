"""
Jobs router: POST /jobs/search with SSE streaming for progress, source statuses, and ranked results.
"""
import asyncio
import logging
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Header, Query
from fastapi.responses import StreamingResponse

from app.section1_foundation_and_providers.providers.base import LLMProvider
from app.section1_foundation_and_providers.providers.registry import get_provider
from app.section1_foundation_and_providers.schemas.job import SearchJobsRequest, SourceStatus
from app.section1_foundation_and_providers.schemas.sse import SSEEvent, SSEEventType
from app.section1_foundation_and_providers.security.security import register_secret
from app.section3_job_sources.registry import fetch_all_sources
from app.section4_ranking_and_search.services.queries import generate_search_queries
from app.section4_ranking_and_search.services.ranking import rank_and_enrich_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)


@router.post("/search")
async def search_jobs(
    request: SearchJobsRequest,
    x_llm_key: Optional[str] = Header(None, alias="X-LLM-Key"),
    x_provider: Optional[str] = Header(None, alias="X-LLM-Provider"),
    x_model: Optional[str] = Header(None, alias="X-LLM-Model"),
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    base_url: Optional[str] = Query(None),
):
    """
    POST /jobs/search: Streams live search execution over SSE:
    1. Query generation
    2. Concurrent 7-source aggregation with live source status updates
    3. Deduplication & 30-day recency filtering
    4. Heuristic ranking (Top 100)
    5. Batched LLM re-scoring (Top 30, semaphore=2)
    6. Final Top 20 ranked jobs emitted under event 'result'.
    """
    # Register secrets in ContextVar
    if x_llm_key:
        register_secret(x_llm_key)
    if request.sources.jsearch_key:
        register_secret(request.sources.jsearch_key)
    if request.sources.adzuna_app_id:
        register_secret(request.sources.adzuna_app_id)
    if request.sources.adzuna_app_key:
        register_secret(request.sources.adzuna_app_key)
    if request.sources.jooble_key:
        register_secret(request.sources.jooble_key)

    chosen_provider = x_provider or provider or "gemini"
    chosen_model = x_model or model

    # Instantiate LLM provider if key available (fallback to heuristic if omitted)
    llm: Optional[LLMProvider] = None
    if x_llm_key or chosen_provider == "ollama":
        try:
            llm = get_provider(
                provider_id=chosen_provider,
                api_key=x_llm_key,
                model=chosen_model,
                custom_url=base_url,
            )
        except Exception as e:
            logger.warning("Could not initialize LLM for re-scoring: %s. Using heuristic only.", str(e))
            llm = None

    async def sse_event_stream() -> AsyncGenerator[str, None]:
        try:
            # Stage 1: Query generation
            yield SSEEvent(
                event=SSEEventType.PROGRESS,
                data={
                    "stage": "preparing",
                    "percent": 10,
                    "message": "Generating high-intent search queries...",
                },
            ).to_sse_format()
            await asyncio.sleep(0.05)

            queries = generate_search_queries(request.profile)

            # Stage 2: Concurrent Multi-source Fetching
            yield SSEEvent(
                event=SSEEventType.PROGRESS,
                data={
                    "stage": "searching",
                    "percent": 25,
                    "message": f"Searching 7 job sources with queries: {', '.join(queries[:2])}...",
                },
            ).to_sse_format()

            queue: asyncio.Queue[SourceStatus] = asyncio.Queue()

            async def status_callback(status_update: SourceStatus):
                await queue.put(status_update)

            # Launch fetch in background task so we can stream source statuses in real-time
            fetch_task = asyncio.create_task(
                fetch_all_sources(queries, request.sources, on_status=status_callback)
            )

            # Drain queue while fetch_task runs
            while not fetch_task.done() or not queue.empty():
                try:
                    status_update = await asyncio.wait_for(queue.get(), timeout=0.2)
                    yield SSEEvent(
                        event=SSEEventType.SOURCE_STATUS,
                        data=status_update.model_dump(),
                    ).to_sse_format()
                except asyncio.TimeoutError:
                    continue

            raw_jobs = await fetch_task

            # Stage 3: Deduplication & Heuristic Ranking
            yield SSEEvent(
                event=SSEEventType.PROGRESS,
                data={
                    "stage": "ranking",
                    "percent": 60,
                    "message": f"Deduplicating and scoring {len(raw_jobs)} aggregated opportunities...",
                },
            ).to_sse_format()
            await asyncio.sleep(0.05)

            # Stage 4: LLM Re-scoring & Calibration
            if llm:
                yield SSEEvent(
                    event=SSEEventType.PROGRESS,
                    data={
                        "stage": "enriching",
                        "percent": 80,
                        "message": f"Calibrating top candidates with {chosen_provider} AI...",
                    },
                ).to_sse_format()

            top_20 = await rank_and_enrich_jobs(raw_jobs, request.profile, llm=llm)

            # Stage 5: Complete & Emit Top 20
            yield SSEEvent(
                event=SSEEventType.PROGRESS,
                data={
                    "stage": "complete",
                    "percent": 100,
                    "message": f"Found {len(top_20)} top matches for your profile.",
                },
            ).to_sse_format()

            yield SSEEvent(
                event=SSEEventType.RESULT,
                data=[job.model_dump() for job in top_20],
            ).to_sse_format()

        except Exception as e:
            logger.error("Job search encountered error: %s", str(e), exc_info=True)
            yield SSEEvent(
                event=SSEEventType.ERROR,
                data={
                    "message": "An error occurred while aggregating and ranking job postings.",
                    "code": "SEARCH_ERROR",
                },
            ).to_sse_format()

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
