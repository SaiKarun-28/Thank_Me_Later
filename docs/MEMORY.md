# Project Memory & Rationale — Stage 1

> This document captures the **operational decisions**, **key dependencies**, and **architectural rationale** behind the implementation of the Resume‑to‑Job Matcher.  It is intended for future maintainers and reviewers to understand why certain choices were made, especially those affecting security, performance, and the Apple‑style UI.

---

## 1. Core Principles (Why)

| Principle | Decision | Reasoning |
|-----------|----------|-----------|
| **Zero‑Persistence** | All resume data lives only in RAM, never written to disk or a DB. | Guarantees privacy‑first stance, complies with PRD non‑negotiables, avoids PII leakage.
| **Bring‑Your‑Own‑Key (BYOK)** | LLM credentials supplied per request via `X‑LLM‑Key`. | Shifts credential ownership to the client, reduces server‑side risk, simplifies secret lifecycle.
| **Per‑Request Secret Redaction** | `ContextVar[set[str]]` + `SecretRedactingLoggingFilter`. | Prevents accidental logging of secrets, satisfies security audit requirements.
| **Apple Fluid Design** | `/apple-design`‑driven motion, translucency, typography. | Delivers a premium, tactile UX that differentiates the product.
| **Hybrid Ranking** | Combine heuristic scoring (40 % skills, 30 % title, 20 % experience/location, 10 % recency) with batched LLM re‑scoring. | Balances speed (heuristic) with quality (LLM) while limiting API costs.
| **Async TTL Cache (10 min)** | Public source adapters (Remotive, Greenhouse, Lever, Ashby). | Reduces rate‑limit hits, lowers latency for repeated queries.
| **SSE Streaming** | All long‑running operations (`/upload`, `/jobs/search`) emit Server‑Sent Events. | Provides real‑time feedback, improves perceived performance.
| **Reduced Motion/Transparency** | Media‑query fallbacks to opacity fades & solid backgrounds. | Meets WCAG 2.1 AA accessibility requirements.

---

## 2. Key Dependencies (What)

- **Backend**: `fastapi`, `uvicorn[standard]`, `httpx`, `python-multipart`, `pdfplumber`, `python-docx`, `pydantic`, `sse-starlette`
- **Frontend**: `next` 14 (App Router), `react` 18, `typescript`, `tailwindcss`, `framer‑motion`, optional `@headlessui/react`
- **LLM Providers**: OpenAI‑compatible endpoints (Groq, OpenRouter, NVIDIA NIM, Cerebras, Mistral, Ollama) and Google Gemini – all accessed via unified `LLMProvider` abstraction.
- **Job Sources**: Remotive (public), Greenhouse/Lever/Ashby (company board scraping), JSearch (RapidAPI), Adzuna, Jooble – each wrapped in an async adapter.
- **Testing**: `pytest`, `pytest‑asyncio`, `playwright` for e2e, GitHub Actions CI stub.
- **Containerization**: Python 3.11 slim for backend, Node 20 for frontend, `docker-compose` for dev orchestration.

---

## 3. Architectural Rationale (How)

1. **Stateless FastAPI Service** – Enables horizontal scaling; each request carries its own secrets, no shared mutable state.
2. **Separate `services/` Layer** – Encapsulates parsing, skill normalization, query generation, ranking logic; keeps `main.py` thin and focused on routing.
3. **Provider Registry** – Allows plug‑in of new LLM providers without touching core code; future‑proofs the system for emerging models.
4. **Source Adapter Base Class** – Enforces a consistent async interface, simplifies mocking for tests and future source additions.
5. **In‑Memory TTL Cache** – Implemented with `asyncio.Lock` + dict of `(key, expiry)`; chosen for minimal footprint and zero external dependencies.
6. **SSE Progress Model** – Emits a `progress` event with `{stage, percent}` payload; client UI can map directly to progress bars without polling.
7. **Design System in Tailwind** – Extends Tailwind config with design tokens from `docs/DESIGN.md`; guarantees visual consistency across components.
8. **Security‑First Middleware** – Registers incoming secrets early, applies redaction filter globally, and validates request bodies via custom `validation_exception_handler`.

---

## 4. Open Questions / Future Considerations

- **Cache Invalidation** – Current TTL is static (10 min). If source APIs provide `ETag`/`Last‑Modified`, we could implement smarter invalidation.
- **Rate‑Limit Back‑off Strategy** – Exponential back‑off is simple; may need jitter or token bucket for high‑traffic scenarios.
- **LLM Cost Monitoring** – Add telemetry to log tokens used per request for budgeting.
- **Extending Job Sources** – Additional ATS (Greenhouse, Lever) may expose GraphQL endpoints; consider a generic GraphQL adapter.
- **Accessibility Audits** – Plan a formal aXe or Lighthouse audit to verify WCAG compliance beyond the basics implemented.

---

## 5. Revision History

| Date (YYYY‑MM‑DD) | Author | Summary |
|-------------------|--------|---------|
| 2026‑10‑18 | Claude Code | Initial MEMORY.md drafted covering principles, deps, rationale, and open questions. |

---

*End of Memory Document.*