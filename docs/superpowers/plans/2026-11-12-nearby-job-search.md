# Nearby Job Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a two-tier job search where the system falls back to "nearby" (same state) jobs if exact location matches are not found.

**Architecture:** Modify the ranking pipeline to first categorize jobs as "exact" or "nearby". If exact jobs are found, return those; otherwise, return nearby jobs with an `is_nearby` indicator.

**Tech Stack:** FastAPI, Pydantic, Python, React, Next.js.

**Spec:** User prompt: "if no jobs were found in User selected location, it should return an message that 'No jobs were found in {user selected location}' then it should display the jobs which are near to the user selected location."

## Global Constraints

- No hardcoded city suggestions.
- Do not silently relax location constraints (must use two-tier logic).
- Preserve existing provider adapters.
- Use British English in all messages.

## Review Focus

- Input: No jobs in city AND no jobs in state. Behavior: Display "No jobs found in {city}" and empty results (Expectation: empty list).
- Input: Malformed raw location string (e.g., "unknown location"). Behavior: Should be treated as ineligible (Expectation: excluded).
- Input: Remote preference is "any" or "remote". Behavior: Should NOT trigger nearby fallback for location (Expectation: return jobs regardless of location).
- Input: Missing `location_data` but has `location`. Behavior: Should normalize and then check nearby (Expectation: attempt nearby).
- Input: Job location is "City A, State B, Country C". Selection: "City A, State B, Country C". Behavior: Exact match (Expectation: marked as exact).

---

### Task 1: Update Job Data Model

**Files:**
- Modify: `backend/app/section1_foundation_and_providers/schemas/job.py`

**Interfaces:**
- Produces: `RankedJob` now includes `is_nearby: bool = False`.

- [ ] **Step 1: Add `is_nearby` field to `RankedJob`**

```python
class RankedJob(JobPosting):
    # ... existing fields
    is_nearby: bool = Field(default=False)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/section1_foundation_and_providers/schemas/job.py
git commit -m "feat(models): add is_nearby to RankedJob"
```

### Task 2: Implement Nearby Location Utility

**Files:**
- Modify: `backend/app/section4_ranking_and_search/services/locations.py`

**Interfaces:**
- Consumes: `JobLocation`, `JobPosting`, `SearchProfile`
- Produces: `is_nearby_location(job: JobPosting, selected: JobLocation) -> bool`

- [ ] **Step 1: Implement `is_nearby_location`**

Check for state and country match (excluding city match requirement).

```python
def is_nearby_location(job: JobPosting, selected: JobLocation) -> bool:
    # Logic: State + Country match (loose)
    # ...
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/section4_ranking_and_search/services/locations.py
git commit -m "feat(services): add is_nearby_location check"
```

### Task 3: Implement Two-Tier Search in Ranking Pipeline

**Files:**
- Modify: `backend/app/section4_ranking_and_search/services/ranking.py`

**Interfaces:**
- Consumes: `is_nearby_location`
- Produces: Updated `rank_and_enrich_jobs` logic.

- [ ] **Step 1: Update `rank_and_enrich_jobs`**

Refactor the filtering loop to maintain two lists: `exact_matches` and `nearby_matches`.

```python
# In rank_and_enrich_jobs loop:
if is_location_eligible(job, selected_loc, profile.remote_preference):
    exact_matches.append(job)
elif is_nearby_location(job, selected_loc):
    nearby_matches.append(job)
```

- [ ] **Step 2: Logic selection**

If `exact_matches` is not empty, use it. Else use `nearby_matches`, setting `is_nearby = True`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/section4_ranking_and_search/services/ranking.py
git commit -m "feat(ranking): implement two-tier location search"
```

### Task 4: Frontend UI Updates

**Files:**
- Modify: `frontend/app/jobs/page.tsx`

**Interfaces:**
- Consumes: `is_nearby` field in `RankedJob`.

- [ ] **Step 1: Update empty state message**

If `isStreaming` is false and no jobs found, display: "No jobs were found in {city}, but here are jobs near {city}".

- [ ] **Step 2: Indicate nearby jobs**

Update `JobCard` or list view to visually indicate if `job.is_nearby` is true.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/jobs/page.tsx
git commit -m "feat(ui): update jobs page for nearby search results"
```
