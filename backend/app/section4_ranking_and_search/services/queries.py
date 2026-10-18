"""
High-intent search query generator for Section 4.
Produces 1 to 3 targeted queries from SearchProfile target roles and primary skills.
"""
from typing import List
from app.section1_foundation_and_providers.schemas.resume import SearchProfile


def generate_search_queries(profile: SearchProfile) -> List[str]:
    """
    Constructs 1-3 targeted queries optimized for job board search engines.
    """
    queries: List[str] = []

    # Sort target roles by confidence descending
    sorted_roles = sorted(profile.target_roles, key=lambda r: r.confidence, reverse=True)

    # 1. Primary target role
    if sorted_roles:
        queries.append(sorted_roles[0].role.strip())

    # 2. Secondary target role if present
    if len(sorted_roles) > 1 and sorted_roles[1].role.strip().lower() != sorted_roles[0].role.strip().lower():
        queries.append(sorted_roles[1].role.strip())

    # 3. Hybrid query: Primary role + Top 2 skills
    top_skills = profile.skills[:2]
    if sorted_roles and top_skills:
        skill_str = " ".join(top_skills)
        hybrid = f"{sorted_roles[0].role.strip()} {skill_str}".strip()
        if hybrid.lower() not in [q.lower() for q in queries]:
            queries.append(hybrid)

    # Fallback if no roles supplied
    if not queries:
        if profile.skills:
            queries.append(" ".join(profile.skills[:3]))
        else:
            queries.append("Software Engineer")

    # Limit to maximum 3 high-intent queries
    return queries[:3]
