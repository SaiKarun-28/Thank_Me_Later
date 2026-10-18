# Implementation Task List — Stage 1

## Phase A: Backend Foundation & Resume Parsing

### A1 — Project Scaffold
- [ ] Create `backend/` directory with a FastAPI entry point (`backend/app/main.py`).
- [ ] Add `requirements.txt` containing:
  ```
  fastapi
  uvicorn[standard]
  httpx
  python-multipart
  pdfplumber
  python-docx
  pydantic
  sse-starlette
  ```
- [ ] Set up standard package layout:
  - `backend/app/__init__.py`
  - `backend/app/schemas/`
  - `backend/app/utils/`
  - `backend/app/providers/`
  - `backend/app/services/`
  - `backend/app/sources/`
- [ ] Configure project‑wide `logging` with `SecretRedactingLoggingFilter`.
- [ ] Enable automatic OpenAPI docs (`/docs`) and JSON schema (`/openapi.json`).

### A2 — Core Schemas (Pydantic v2)
- [ ] `app/schemas/sse.py` – `SSEEventType` (`"progress"`, `"source_status"`, `"result"`, `"error"`) and `SSEEvent` model.
- [ ] `app/schemas/resume.py` – definitions for:
  - `TargetRole`
  - `ExperienceItem`
  - `EducationItem`
  - `ParsedProfile`
  - `ConfirmedProfile`
  - `SearchProfile`
  - helper `calculate_default_experience_level()`.
- [ ] `app/schemas/job.py` – `JobPosting`, `RankedJob`, `SearchJobsRequest`, `JobSourceConfig`.

### A3 — Security & Secret Redaction
- [ ] `app/utils/security.py` – implement:
  - `active_secrets: ContextVar[set[str]]`
  - `SecretRedactingLoggingFilter`
  - `sanitize_url()` (enforce `HttpUrl` scheme and drop unsafe URLs)
  - `register_secret(value: str)` helper used by request middleware.
  - FastAPI `validation_exception_handler` that strips secret values from 422 payloads.
- [ ] Silence `httpx` and `httpcore` loggers to `WARNING` level.

### A4 — Provider Infrastructure
- [ ] `app/providers/base.py` – abstract `LLMProvider` with `test_connection()` and `json_completion()` + generic 1‑retry exponential backoff.
- [ ] `app/providers/openai_compat.py` – support for Groq, OpenRouter, NVIDIA NIM, Cerebras, Mistral, and local Ollama (via `/chat/completions`).
- [ ] `app/providers/gemini.py` – Gemini API wrapper using `x-goog-api-key` header.
- [ ] `app/providers/registry.py` – provider catalog, default model map, and `get_provider(name)` factory.
- [ ] `POST /settings/test` endpoint – validates supplied `X-LLM-Key` (or other credentials) and returns success/failure.

### A5 – Resume Upload & Hardening (`POST /upload`)
- [ ] Validate multipart file size ≤ 5 MiB.
- [ ] Magic‑byte inspection (`%PDF` for PDFs, `PK\x03\x04` for DOCX/ZIP).
- [ ] DOCX zip‑bomb guard – ensure total uncompressed size < 20 MiB.
- [ ] PDF page limit – reject if > 10 pages.
- [ ] Off‑load CPU‑heavy extraction to thread pool via `asyncio.to_thread` with `asyncio.wait_for(..., timeout=10.0)`.
- [ ] Use `pdfplumber` for PDFs and `python-docx` for DOCX.
- [ ] Guard against image‑only scans – reject if extracted text < 50 characters with a clear “scanned document” error.
- [ ] Stream parsing progress via SSE (`event: "progress"`).

### A6 – Profile Normalization & Confirmation UI
- [ ] Convert `ParsedProfile` into an editable `ConfirmedProfile` on the frontend (React state).
- [ ] Strip PII and raw bullets to generate minimal `SearchProfile` before sending to `/jobs/search`.

## Phase B: Job Sources, Aggregation & Hybrid Ranking

### B1 – Source Adapters (Async)
- [ ] Implement a base `SourceAdapter` in `app/sources/base.py` with `async fetch(query: str) -> list[JobPosting]` and standardized timeout handling.
- [ ] Build adapters for:
  - `remotive.py` (public, keyless)
  - `greenhouse.py`, `lever.py`, `ashby.py` (company board scraping, keyless)
  - `jsearch.py` (RapidAPI)
  - `adzuna.py` (REST API, token‑protected)
  - `jooble.py` (REST API, token‑protected)
- [ ] Add `cache.py` – async in‑memory TTL cache (10 min) for public sources.

### B2 – Concurrent Fetch Pipeline
- [ ] In `app/services/queries.py` build the high‑level query generator (1‑3 high‑intent strings per target role/skill set).
- [ ] In `app/services/ranking.py` implement:
  - Normalization & deduplication by `(title.lower(), company.lower(), location.lower())`.
  - Heuristic scoring (skill overlap 40 %, title similarity 30 %, experience/location 20 %, recency 10 %).
  - Select top‑100, then top‑30 for LLM enrichment.
  - Batched LLM re‑scoring (batch size 5, `asyncio.Semaphore(2)`, exponential backoff on 429).
  - Final combined score = 0.5 × heuristic + 0.5 × LLM.
- [ ] Ensure graceful handling of `return_exceptions=True` – failing source should not abort the whole pipeline.

### B3 – SSE Streaming of Search Workflow
- [ ] `/jobs/search` endpoint returns `text/event-stream`.
  - Emit `source_status` events for each source (pending/loading/success/error).
  - Emit `progress` events for ranking stages.
  - Emit final `result` events with top‑20 `RankedJob` payloads.

## Phase C: Next.js Frontend (App Router)

### C1 – Project Bootstrap
- [ ] `frontend/` directory with `next.config.js` (enable experimental `appDir`).
- [ ] Install dependencies:
  - `react` 18, `next` 14, `typescript`, `tailwindcss`, `framer-motion`, `@headlessui/react` (optional), `sse-starlette-client` (or custom EventSource wrapper).
- [ ] Configure Tailwind with `theme.extend` for the design‑system colors, spacing (8‑pt grid), and typography scale defined in `docs/DESIGN.md`.

### C2 – Core Pages & Components
- **Upload Page** (`/upload`)
  - Drag‑and‑drop zone with dashed border, animated spring on `dragover`.
  - SSE listener for parsing progress.
  - Display parsed skill chips for confirmation.
- **Confirmation Page** (`/profile`)
  - Editable chip groups (skills, target roles).
  - Location & remote‑preference selectors.
  - "Run Search" button triggers `/jobs/search`.
- **Results Feed** (`/results`)
  - Card component per `RankedJob` (see `docs/DESIGN.md` component blueprint).
  - Expandable description with spring layout animation.
  - Apply CTA with `rel="noopener noreferrer" target="_blank"`.
- **Global State** – use React context or simple `useState` hooks; avoid Redux unless a later phase demands it.
- **SSE Hook** – custom hook `useSSE(url, onEvent)` that reconnects on disconnects.

### C3 – Accessibility & Preferences
- [ ] Respect `prefers-reduced-motion` & `prefers-reduced-transparency` via CSS media queries (fallback to opacity fades).
- [ ] Ensure all interactive elements are keyboard focusable and have ARIA labels.
- [ ] Provide high‑contrast mode via `prefers-contrast` media query.

## Phase D: Docker, Verification & Documentation

### D1 – Containerization
- [ ] Write `Dockerfile` for backend (Python 3.11 slim) exposing port 8000.
- [ ] Write `Dockerfile` for frontend (Node 20 -> static export via `next build && next export`).
- [ ] Compose file `docker-compose.yml` to spin both services together for local dev.

### D2 – Testing & CI
- [ ] Add `pytest` suite covering:
  - Schema validation.
  - Security filter redaction.
  - Upload hardening edge cases (oversized, wrong magic bytes, zip‑bomb).
  - Source adapters (mocked HTTPX client).
  - Ranking heuristics.
- [ ] Add Playwright end‑to‑end test for the upload → results flow.
- [ ] CI‑pipeline stub (GitHub Actions) – lint, test, build Docker images.

### D3 – Final Documentation
- [ ] Ensure all docs (`PRD.md`, `ARCHITECTURE.md`, `RULES.md`, `DESIGN.md`, `TASKS.md`, `MEMORY.md`) are up‑to‑date.
- [ ] Add generated OpenAPI spec link to the README.
- [ ] Verify that the repo root contains a `README.md` with quick‑start instructions.

---

**All tasks are ordered for minimal context‑switching.** Complete Phase A before moving to Phase B, then Phase C, and finally Phase D. Adjust the task list as implementation progress dictates.
