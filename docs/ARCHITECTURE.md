# Architecture Document — Stage 1: Resume-to-Job Matcher

## 1. System Overview & Architecture Diagram

Stage 1 is structured around a decoupled, stateless **FastAPI** backend and a **Next.js 14 (App Router)** frontend. It operates strictly under a **Bring Your Own Key (BYOK)** and **Zero Persistence** architecture.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       NEXT.JS 14 FRONTEND (CLIENT)                         │
│                                                                             │
│  ┌───────────────────────┐   ┌──────────────────────┐   ┌─────────────────┐ │
│  │     Upload Page       │   │   Confirmation Page  │   │  Results Feed   │ │
│  │ (PDF/DOCX Dropzone)   │   │(Profile Customization│   │ (Ranked Cards,  │ │
│  │ (Direct SSE Listener) │   │ & SearchProfile Gen) │   │  Skills Badges) │ │
│  └───────────┬───────────┘   └──────────┬───────────┘   └────────▲────────┘ │
│              │                          │                        │          │
│              │ Multipart POST           │ POST /jobs/search      │ SSE Feed │
│              │ + X-LLM-Key              │ (SearchProfile only)   │          │
│              ▼                          ▼                        │          │
│  ┌───────────────────────────────────────────────────────────────┴────────┐ │
│  │                    Client Storage & Security Layer                    │ │
│  │   sessionStorage (default) / localStorage (with explicit alert)        │ │
│  │   LLM Keys, API Credentials, ConfirmedProfile, ParsedProfile           │ │
│  └──────────────────────────────────────┬─────────────────────────────────┘ │
└─────────────────────────────────────────┼───────────────────────────────────┘
                                          │ HTTP / SSE (CORS restricted)
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND (STATELESS)                         │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      Per-Request Security Layer                       │  │
│  │  - ContextVar Secret Registry (scrubs LLM keys, RapidAPI keys, etc.)  │  │
│  │  - SecretRedactingLoggingFilter (masks secrets in all logs)           │  │
│  │  - Validation Exception Handler (clears input reflection)             │  │
│  │  - In-Memory Processing Pipeline (zero disk I/O, zero database)       │  │
│  └──────────────────────────────────┬────────────────────────────────────┘  │
│                                     │                                       │
│          ┌──────────────────────────┴──────────────────────────┐            │
│          ▼                                                     ▼            │
│  ┌──────────────────────────────┐              ┌──────────────────────────┐ │
│  │   POST /upload (SSE)         │              │  POST /jobs/search (SSE) │ │
│  │  - Magic bytes inspection    │              │  - Query Generator       │ │
│  │  - Zip-bomb inspection       │              │  - 7 Source Adapters     │ │
│  │  - pdfplumber (to_thread)    │              │    (10-min TTL Cache)    │ │
│  │  - Delimited LLM Extraction  │              │  - HTML Stripper         │ │
│  │  - Emit ParsedProfile (SSE)  │              │  - Skill Normalizer      │ │
│  └──────────────┬───────────────┘              │  - Heuristic Rank (100)  │ │
│                 │                              │  - Batched LLM Re-score  │ │
│                 │                              │    (Top 30, sem=2)       │ │
│                 ▼                              │  - Emit Top 20 (SSE)     │ │
│  ┌──────────────────────────────┐              └─────────────┬────────────┘ │
│  │     LLM Provider Engine      │                            │              │
│  │  - OpenAI-Compat (Groq, etc.)│◄───────────────────────────┘              │
│  │  - Google Gemini             │                                           │
│  └──────────────────────────────┘                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Design & Responsibilities

### 2.1 Backend Modules (`backend/app/`)

- **`main.py`**:
  - FastAPI application entry point.
  - Registers security middleware, exception handlers, log sanitizers, and API routers (`/upload`, `/jobs`, `/settings`).
  - Implements CORS middleware configured strictly for development origins (`http://localhost:3000`).
- **`schemas/`**:
  - `sse.py`: Standardizes the `SSEEvent` protocol across all streaming endpoints.
  - `resume.py`: Defines `ParsedProfile`, `ConfirmedProfile`, `SearchProfile`, `TargetRole`, `ExperienceItem`, `EducationItem`, and `calculate_default_experience_level()`.
  - `job.py`: Defines `JobPosting`, `RankedJob`, `SearchJobsRequest`, and `JobSourceConfig`.
- **`utils/security.py`**:
  - `active_secrets: ContextVar[set[str]]`: Request-scoped isolated registry for sensitive values.
  - `SecretRedactingLoggingFilter`: Replaces exact active secrets and common token patterns (`Bearer ...`, `AIza...`, `gsk_...`) with `[REDACTED]`.
  - `sanitize_url()`: Enforces HTTP/HTTPS protocol checks on outbound apply links and image links.
  - `validation_exception_handler()`: Strips client payload input reflection from FastAPI 422 errors to prevent key reflection.
- **`providers/`**:
  - `base.py`: Declares `LLMProvider` abstract base class with `test_connection()` and `json_completion()`. Implements 1-retry backoff and standard error normalization.
  - `openai_compat.py`: Handles Groq, OpenRouter, NVIDIA NIM, Cerebras, Mistral, and local Ollama (`/chat/completions`).
  - `gemini.py`: Handles Google Gemini API requests passing keys safely via `x-goog-api-key` header (never in URL parameters).
  - `registry.py`: Provider catalog, default models, and provider factory.
- **`services/`**:
  - `parsing.py`: Streamlined in-memory file parsing. Validates magic bytes, guards against zip bombs, runs `pdfplumber` inside worker threads (`asyncio.to_thread` with 10s timeout), detects image-only scans, and executes delimited LLM extraction into `ParsedProfile`.
  - `skills.py`: Normalizes skill tokens using a canonical dictionary (`JS` ↔ `JavaScript`, `K8s` ↔ `Kubernetes`, `Node` ↔ `Node.js`, etc.) and calculates multi-set overlap.
  - `queries.py`: Generates 1–3 high-intent search queries based on `target_roles` and top skills.
  - `ranking.py`: Implements the hybrid ranking funnel:
    - Normalization and deduplication by `(title, company, location)`.
    - Heuristic scoring (40% skills, 30% title similarity, 20% experience/location fit, 10% recency boost).
    - Top 30 candidate selection for LLM enrichment.
    - Batched LLM re-scoring (batches of 5, semaphore=2, 429 exponential backoff, JD truncated to 1,500 chars).
    - Combined score calculation: $0.5 \times \text{Heuristic} + 0.5 \times \text{LLM}$.
- **`sources/`**:
  - `base.py`: Base adapter class with standard interface and timeout handling.
  - `cache.py`: Asynchronous in-memory 10-minute TTL cache for public job boards.
  - `jsearch.py`, `adzuna.py`, `jooble.py`: Paid/freemium API source adapters.
  - `remotive.py`: Public remote jobs API adapter.
  - `greenhouse.py`, `lever.py`, `ashby.py`: Keyless public company board adapters with local keyword filtering.

---

## 3. Data Flow & Security Boundaries

### 3.1 BYOK & Request Secret Redaction
1. The client sends `X-LLM-Key` and any platform credentials in request bodies.
2. FastAPI middleware registers these raw strings into `active_secrets` `ContextVar`.
3. All outgoing log records pass through `SecretRedactingLoggingFilter`, matching against both:
   - Specific registered secret strings.
   - Known token regex patterns (`gsk_[a-zA-Z0-9]{32,}`, `AIza[0-9A-Za-z-_]{35}`, etc.).
4. In case of unhandled errors or Pydantic validation exceptions, custom handlers ensure sensitive inputs are purged from the response body.

### 3.2 Lightweight `SearchProfile` Boundary
To protect candidate privacy:
- `ParsedProfile` (containing name, raw text, past company details, and project bullets) stays on the client after `/upload`.
- When searching (`POST /jobs/search`), the client sends only `SearchProfile`:
  ```json
  {
    "target_roles": [{"role": "Full Stack Engineer", "confidence": 0.95}],
    "skills": ["TypeScript", "React", "Python", "FastAPI"],
    "location": "San Francisco, CA",
    "remote_preference": "remote",
    "experience_level": "mid",
    "years_experience": 4.5
  }
  ```
- No resume text, contact info, or personal narratives are ever transmitted across search endpoints or passed to external job search APIs.

---

## 4. Concurrency & Performance Model

1. **Upload Pipeline**:
   - Extraction runs off the async event loop using `asyncio.to_thread` wrapped in `asyncio.wait_for(timeout=10.0)` to protect server responsiveness.
2. **Multi-Source Fetching**:
   - `asyncio.gather(*tasks, return_exceptions=True)` executes all 7 adapters concurrently with an isolated 10-second timeout per source.
   - Public sources (Greenhouse, Lever, Ashby, Remotive) hit an in-memory TTL cache (10 min) keyed on `(source_id, query_or_slug)` to avoid rate limits and minimize latency.
3. **LLM Enrichment Pipeline**:
   - Top 100 jobs filtered to Top 30.
   - Evaluated in chunks of 5 using `asyncio.Semaphore(2)` (limiting concurrent LLM requests to 2).
   - If an LLM call encounters HTTP 429, it applies an exponential backoff (1s, 2s) before falling back cleanly to heuristic scoring.
4. **SSE Streaming**:
   - Responses stream instantly using `fastapi.responses.StreamingResponse(..., media_type="text/event-stream")`.
   - Keepalive pings (`: ping\n\n`) every 15s keep client connections stable over long search iterations.

---

## 5. Technology Stack Summary

| Layer | Technology | Justification |
|---|---|---|
| **Frontend Framework** | Next.js 14 (App Router) | Server-rendered shells, React 18 client components, built-in optimization |
| **Styling** | Tailwind CSS | Utility-first, precise Apple-grade typography and translucent material system |
| **Motion & Gestures** | Framer Motion / Motion | Spring physics (`damping: 1.0`, `response: 0.3-0.4`), 1:1 gesture tracking |
| **Backend Framework** | FastAPI (Python 3.11+) | Async native, Pydantic type safety, fast SSE streaming |
| **Document Parsing** | pdfplumber & python-docx | Robust text and layout extraction in memory |
| **HTTP Client** | httpx (async) | Async connection pooling, clean timeouts, and SSL verification |
| **Testing** | pytest, pytest-asyncio, Playwright | High-speed unit, security, and integration coverage |
