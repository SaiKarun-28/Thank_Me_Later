# Engineering & Design Rules — Stage 1: Resume-to-Job Matcher

## 1. Core Architectural & Security Rules (Non-Negotiable)

1. **Zero Backend Persistence**:
   - Resumes, parsed profiles, raw text, and API keys MUST NEVER be written to disk, SQLite, Redis, or any database.
   - Processing is 100% ephemeral and occurs strictly in RAM.
   - Any log, exception trace, or telemetry recording PII or raw resume bullets is a critical defect.

2. **Bring Your Own Key (BYOK) Isolation**:
   - All LLM interactions use client-provided credentials supplied per-request via the `X-LLM-Key` HTTP header.
   - Credentials must never be written to `.env` or shared across user sessions on the backend.
   - Client storage defaults strictly to `sessionStorage` (cleared on tab close). `localStorage` is permitted only via explicit user opt-in with a security warning.

3. **Per-Request Key Redaction**:
   - Any secret string (LLM key, RapidAPI key, Adzuna/Jooble token) must be registered in the request-scoped `ContextVar[set[str]]`.
   - The custom `SecretRedactingLoggingFilter` must scrub registered secrets by exact value and regex pattern across all logging streams.
   - Custom `RequestValidationError` handlers must strip the `"input"` key and scrub messages so validation errors never leak reflected secret values.
   - `httpx` and `httpcore` loggers must be silenced to `WARNING` to prevent URL query parameter logging.

4. **Privacy-Preserving Search Boundary**:
   - The client MUST NOT send `ParsedProfile` or `ConfirmedProfile` (which contain raw text, past employers, and project bullets) to `/jobs/search`.
   - Only the minimal `SearchProfile` (`target_roles`, `skills`, `location`, `remote_preference`, `experience_level`, `years_experience`) is permitted in search payloads.

5. **Safe URL Validation**:
   - All `apply_url` links from job boards must be validated against `HttpUrl` (HTTP/HTTPS schemes only).
   - Any job posting with a malformed or non-web scheme (`javascript:`, `file:`, internal network IP) must be silently dropped without failing the source.
   - All external outbound links on the frontend must have `rel="noopener noreferrer"` and `target="_blank"`.

6. **Upload Hardening**:
   - File uploads must not exceed 5 MB.
   - Magic bytes must be verified (`%PDF` for PDF, `PK\x03\x04` for DOCX).
   - DOCX uncompressed size must be verified < 20 MB (zip-bomb defense).
   - PDF pages must be limited to 10. `pdfplumber` must execute in `asyncio.to_thread` with an `asyncio.wait_for(timeout=10.0)` guard.
   - Extracted text < 50 characters must be rejected with an actionable scanned/image-only error.

---

## 2. Coding Standards & Idioms

### Backend (Python / FastAPI)
- **Typing & Validation**: Strict Pydantic v2 schemas for all payloads and internal models. Explicit type hints on all functions.
- **Asynchronous Execution**:
  - Pure async I/O for network calls with `httpx.AsyncClient`.
  - CPU/blocking operations (`pdfplumber`, `python-docx`) must be isolated with `asyncio.to_thread`.
  - External network calls must be bounded by explicit timeouts (e.g., 10s per job source).
- **Concurrency & Resiliency**:
  - Source gathering must use `asyncio.gather(*tasks, return_exceptions=True)` so one failing source never crashes the search.
  - LLM re-scoring must run in batches of 5 with `asyncio.Semaphore(2)` and exponential backoff on HTTP 429.
  - Public sources (Greenhouse, Lever, Ashby, Remotive) must use an in-memory async TTL cache (10 minutes).
- **Error Handling**:
  - Always return structured JSON errors or SSE error events (`{"event": "error", "data": {"message": str, "code": str}}`).
  - Translate upstream provider errors (401 Invalid Key, 429 Quota/Rate Limit, timeouts) into clear, friendly client messages.

### Frontend (Next.js / TypeScript / React)
- **Strict TypeScript**: `noImplicitAny: true`, zero `any` types in production logic.
- **Client/Server Boundary**: Explicit `"use client"` directives for interactive forms, dropzones, and SSE listeners.
- **Unified SSE Types**: Mirror backend `SSEEventType` and `SSEEvent` definitions exactly.
- **State Management**:
  - No bloated global state stores (Zustand/Redux) unless necessary; clean React hooks + storage utilities.
  - Graceful disconnection handling and reconnect guards on EventSource/fetch streams.

---

## 3. Apple Design Principles (`/apple-design`)

1. **Fluid Motion & Physics**:
   - Use springs instead of fixed-duration cubic-béziers for interactive elements.
   - Default UI spring: critically damped (`damping: 1.0`, `response: 0.3–0.4`s / `bounce: 0`).
   - Momentum/gesture spring: slightly under-damped (`damping: ~0.8`, `response: 0.3–0.4`s / `bounce: 0.2`) only after a physical flick or drag.
2. **Instant Response**:
   - Visual feedback on pointer-down/touch-down (scale: `0.97` or subtle background tint), not delayed on release.
   - Eliminate unnecessary input debounces and click latencies.
3. **Interruptibility & Spatial Consistency**:
   - Animations must be interruptible mid-flight without locking input.
   - Exit transitions must mirror entry transitions (same axis and spatial origin).
4. **Materials & Depth**:
   - Translucent navigation bars and headers with `backdrop-filter: blur(20px)` and subtle borders.
   - Hierarchical elevation: heavier blur and shadow for higher-level surfaces (sheets/cards), lighter for inline controls.
5. **Typography & Hierarchy**:
   - System font stacks (`system-ui, -apple-system, BlinkMacSystemFont`).
   - Tight tracking (`letter-spacing: -0.02em`) on large display headings, relaxed leading on body copy.
   - Use font weight and contrast rather than oversaturated colors to establish visual hierarchy.
6. **Accessibility & Preferences**:
   - Honor `prefers-reduced-motion` with clean cross-fades instead of spring transforms.
   - Honor `prefers-reduced-transparency` with solid backgrounds.

---

## 4. Ponytail Senior Efficiency Principles

1. **The Ladder**:
   - Does this need to exist? If speculative, skip it (YAGNI).
   - Use stdlib (`contextvars`, `dataclasses`, `asyncio`, `urllib`) and native platform features over third-party bloat.
   - The first lazy solution that works correctly is the right one.
2. **Root Cause Fixes**:
   - Always fix bugs at the single shared point of truth, never patch symptoms in individual callers.
3. **Fewest Files & Shortest Working Diff**:
   - No boilerplate scaffolding "for later".
   - Keep abstractions justified by at least two distinct, active consumers.
4. **Deliberate Simplifications**:
   - Any intentional trade-off must be marked with `# ponytail: [rationale]` explaining the constraint and future upgrade path.

---

## 5. Git & Commit Guidelines

- Commit messages must be clear, concise, and written in the imperative mood.
- Every commit message must end with:
  `Co-Authored-By: Gemini <gemini@google.com>`
- Pull request descriptions must conclude with:
  `🤖 Generated with [Gemini](https://gemini.google.com)`
