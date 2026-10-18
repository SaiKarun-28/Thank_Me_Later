# Product Requirements Document (PRD) — Stage 1: Resume-to-Job Matcher

## 1. Executive Summary
Stage 1 of **Thank Me Later** is a high-performance, privacy-first web application designed to eliminate friction in job hunting. Users upload their resume (PDF or DOCX), which is processed entirely in-memory with zero backend persistence. The system extracts structured profile data via user-provided LLM credentials (Bring Your Own Key — BYOK), allows user review and customization, searches 7 job boards and public ATS platforms concurrently, ranks opportunities using a hybrid scoring algorithm (heuristic + batched LLM evaluation), and presents actionable, ranked job cards with match rationales, skill overlaps, and verified direct apply links.

---

## 2. Target Audience & Personas
- **Active Job Seekers**: Software engineers, product managers, and tech professionals seeking high-relevance matches tailored to their actual skills and past experience without sign-up walls.
- **Privacy-Conscious Candidates**: Users who refuse to have their personal resumes, contact details, or job search activity stored, indexed, or sold to recruiters.
- **Power Users / Developers**: Users comfortable bringing their own LLM API keys (Groq, Gemini, OpenRouter, Cerebras, NVIDIA NIM, Mistral, Ollama) to obtain unthrottled, fast, AI-powered matching at cost price (or free tier).

---

## 3. Core Principles & Non-Negotiables
1. **Zero Backend Persistence**: Resumes, parsed profiles, and API keys are never stored on disk or in a backend database. Processing occurs exclusively in memory.
2. **Bring Your Own Key (BYOK)**: All LLM requests execute using client-supplied API keys transmitted via HTTP headers (`X-LLM-Key`). Keys stay on the client (`sessionStorage` default, optional warning-gated `localStorage`).
3. **Hardened Secret Redaction**: Active request secrets (LLM keys, RapidAPI keys, Adzuna/Jooble tokens) are registered in a per-request `contextvars.ContextVar` and scrubbed from all logs, traces, and error outputs by exact value matching.
4. **Real-time Feedback**: Resume parsing and job searching utilize Server-Sent Events (SSE) streaming progress and status to the user.
5. **No Broken Links**: Apply URLs are validated strictly against HTTP/HTTPS schemes; invalid or malformed links are silently excluded.
6. **Fluid & Tactile UX**: Built with Apple-inspired fluid design principles—instant response on press, spring physics, translucent materials, and thoughtful typography.

---

## 4. End-to-End User Flow
```
[User Landing Page]
       │
       ▼
[Enter Settings / BYOK] ── (API Key test connection verified)
       │
       ▼
[Upload Resume] ────────── (PDF/DOCX max 5MB, in-memory validation, SSE progress)
       │
       ▼
[Confirm & Refine Profile] (Review skills, target roles, experience level, location)
       │
       ▼
[Run Search] ───────────── (Minimal SearchProfile sent; 7 sources queried concurrently)
       │
       ▼
[Rank & Enrich] ────────── (Deduplication -> Heuristic top 100 -> Batched LLM re-score top 30)
       │
       ▼
[Job Results Feed] ─────── (Top 20 matches, match score %, reasons, skills diff, direct apply)
```

---

## 5. Detailed Feature Specifications

### 5.1 Settings & BYOK Management
- **Provider Support**:
  - OpenAI-compatible endpoints: Groq, OpenRouter, NVIDIA NIM, Cerebras, Mistral, Ollama (localhost only).
  - Google Gemini (`x-goog-api-key` header).
- **Security Safeguards**:
  - Custom base URL input locked down: allowed only when provider is `ollama` and environment is local/dev, strictly pointing to `http://localhost:11434` or `http://host.docker.internal:11434`.
  - Model names validated against `^[a-zA-Z0-9_\-.:/]{1,64}$`.
  - "Test Connection" endpoint (`POST /settings/test`) validating credentials before searching.
- **Client Storage Choice**:
  - Default: `sessionStorage` (cleared on tab close).
  - Optional: `localStorage` (shows explicit security warning modal regarding browser script access).

### 5.2 Resume Upload & Ingestion
- **File Handling**: Multipart POST to `/upload`, max 5 MB, processed entirely in RAM.
- **File Validation & Hardening**:
  - Magic-byte verification: `%PDF` for PDF, `PK\x03\x04` for DOCX.
  - Zip-bomb defense for DOCX: validates cumulative uncompressed payload remains under 20 MB.
  - Page ceiling: max 10 pages for PDF.
  - Threaded extraction: `pdfplumber` runs inside `asyncio.to_thread` bounded by `asyncio.wait_for(timeout=10.0)`.
  - Empty text guard: if extracted text < 50 characters, returns friendly actionable error prompting for a text-based document (rejecting image-only scans).
- **Streaming Response**: SSE channel reporting `stage` ("reading", "extracting", "analyzing", "complete") with percentage progress.

### 5.3 LLM Extraction & Profile Normalization
- Prompt-injection hardened extraction prompt using XML delimiters (`<resume_document>...</resume_document>`).
- Generates `ParsedProfile`:
  - `name`, `skills`, `years_experience`, `education`, `past_titles`, `domains`, `target_roles` (with confidence 0.0–1.0), `experience`, `projects`, `certifications`, `contact`.
- Automatic experience level derivation:
  - `< 1 yr`: `fresher`
  - `1–3 yrs`: `junior`
  - `3–6 yrs`: `mid`
  - `6+ yrs`: `senior`

### 5.4 Profile Confirmation Screen
- Editable chip arrays for `skills` and `target_roles`.
- Configurable `location`, `remote_preference` (`remote`, `hybrid`, `onsite`, `any`), and `experience_level`.
- Produces `ConfirmedProfile` on the frontend.
- When triggering search, the frontend strips private resume data (raw text, project bullets, employment history) and generates a lightweight `SearchProfile`.

### 5.5 Multi-Source Job Aggregation
Concurrently queries 7 platforms via `asyncio.gather(*tasks, return_exceptions=True)` with 10s per-source timeout:
1. **Remotive**: Public remote jobs API (keyless, with 10-minute in-memory TTL cache and Remotive attribution).
2. **Greenhouse**: Keyless board endpoints (`/v1/boards/{slug}/jobs`), filtered locally by target keywords; 10-min TTL cache.
3. **Lever**: Keyless board endpoints (`/v1/postings/{slug}`), filtered locally; 10-min TTL cache.
4. **Ashby**: Keyless board endpoints (`/posting-api/job-board/{slug}`), filtered locally; 10-min TTL cache.
5. **JSearch (RapidAPI)**: Query-based API for broader web postings.
6. **Adzuna**: International job index with country routing (query params sanitized).
7. **Jooble**: Global job index via JSON POST.

### 5.6 Data Normalization, Stripping & Deduplication
- **HTML Stripping**: All incoming descriptions stripped of HTML tags and normalized to plain text before processing.
- **Link Sanitization**: Every job posting's `apply_url` is verified with `HttpUrl` (HTTP/HTTPS only). Invalid URLs are dropped silently without failing the source.
- **Deduplication**: Case- and whitespace-normalized composite key: `(title.lower().strip(), company.lower().strip(), location.lower().strip())`.

### 5.7 Skill Mapping & Hybrid Ranking
- **Skill Normalization**: Canonical alias dictionary (`JS` ↔ `JavaScript`, `K8s` ↔ `Kubernetes`, `React.js` ↔ `React`, `TS` ↔ `TypeScript`, `Node` ↔ `Node.js`, `AWS` ↔ `Amazon Web Services`, etc.).
- **Heuristic Scoring (0–100)**:
  - 40% Skill overlap (using canonical skill map).
  - 30% Target role title similarity.
  - 20% Experience level & location/remote fit.
  - 10% Recency boost (within 7 days).
- **Candidate Funnel**:
  - Filter top 100 deduplicated postings.
  - Pass top 30 to LLM re-scoring.

### 5.8 Batched LLM Re-scoring & Calibration
- JDs truncated to ~1,500 characters to conserve tokens and reduce latency.
- Processed in batches of 5 candidates with `asyncio.Semaphore(2)` (concurrency 2) and exponential backoff on HTTP 429.
- LLM outputs:
  - Calibrated `match_score` (0–100).
  - Concise `match_reason` (1 clear sentence).
  - `required_skills`, `matched_skills`, `missing_skills`.
- Fallback: if LLM fails or errors out, automatically fallback to heuristic scores.
- Final Combined Score:
  $$\text{Final Score} = 0.5 \times \text{Heuristic Score} + 0.5 \times \text{LLM Score}$$
  (or 100% Heuristic Score if LLM was skipped/unavailable).
- Returns Top 20 ranked jobs to the client.

### 5.9 Results Presentation
- Card feed ranked by final score.
- Match badge with visual score indicator.
- Single-sentence match rationale.
- Skill badges: Green (matched skills) vs. Subtle Slate (missing skills).
- Collapsible job description with smooth spring animation.
- Direct apply CTA with `rel="noopener noreferrer"` and `target="_blank"`.

---

## 6. Non-Functional Requirements
- **Performance**:
  - Resume upload & extraction: < 5s total.
  - Concurrent search + heuristic ranking: < 4s.
  - Top 30 LLM enrichment: < 8s with batched execution.
- **Security & Privacy**:
  - OWASP Top 10 compliance for web uploads (anti-zip bomb, file size constraints, magic byte validation).
  - Zero server-side caching of personally identifiable information (PII).
  - Redaction of all keys and credential values in logging and error handling.
- **Accessibility**:
  - WCAG 2.1 AA compliance, high contrast text, full keyboard navigation, `prefers-reduced-motion` and `prefers-reduced-transparency` media query support.
