"""
Section 4: Hybrid Ranking & Search Engine.
"""
from app.section4_ranking_and_search.services.skills import (
    normalize_skill,
    calculate_skill_overlap,
    CANONICAL_SKILL_MAP,
)
from app.section4_ranking_and_search.services.queries import generate_search_queries
from app.section4_ranking_and_search.services.ranking import (
    deduplicate_jobs,
    filter_recency_30_days,
    calculate_heuristic_score,
    rank_and_enrich_jobs,
)
from app.section4_ranking_and_search.routers.jobs import router as jobs_router

__all__ = [
    "normalize_skill",
    "calculate_skill_overlap",
    "CANONICAL_SKILL_MAP",
    "generate_search_queries",
    "deduplicate_jobs",
    "filter_recency_30_days",
    "calculate_heuristic_score",
    "rank_and_enrich_jobs",
    "jobs_router",
]
