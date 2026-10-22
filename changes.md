# Summary of Changes — Thank Me Later

**Date:** October 2026  
**Scope:** Frontend UI enhancements, theme support, state reconciliation, robust error/fallback handling, save action feedback animations, and provider free-tier model updates.

---

## 1. Executive Summary

Following comprehensive audits of UI behavior, error states, storage resilience, and model availability across providers, a series of production-grade improvements and bug fixes were implemented across both the FastAPI backend and Next.js frontend. 

All changes maintain strict adherence to stateless BYOK architecture, security redaction boundaries, and zero-flash UI rendering principles.

---

## 2. Detailed Breakdown of Changes

### A. Frontend UI/UX & Theming
* **Explicit Light/Dark Theme Support:**
  * Added a user-selectable theme toggle in the shared navigation header (`AppShell`), persisting preferences to `localStorage`.
  * Implemented a zero-flash initialization inline script in `app/layout.tsx` that inspects stored preferences with a fallback to `prefers-color-scheme`.
  * Harmonized CSS custom properties (`--background`, `--foreground`, `--card`, `--border`, `--muted`, `--accent`) across both light and dark themes.

* **Provider & Model State Reconciliation:**
  * Resolved "blank select" bugs in the settings view by proactively reconciling stored settings against active provider and model catalogues upon mount and remote metadata fetches.

* **Robust Endpoint Validation & Fallback UI:**
  * Added protocol-aware validation for custom backend endpoints to reject malformed URLs or credentials before saving.
  * Introduced non-blocking fallback status banners in the Settings UI and Job Sources form when live backend metadata requests fail, ensuring the UI remains fully usable with local defaults.

* **Interactive Save Button Feedback:**
  * Added visual feedback to the "Save settings" button: transitions from idle (`Save`) to a circling spinner (`LoaderCircle`) during save, followed by a success confirmation state (`CheckCircle2`).

### B. Provider Free-Tier Model & Switching Fixes
* **Resolved "Model Not Found" Root Causes:**
  * Fixed model reconciliation in `frontend/app/settings/page.tsx` where switching providers retained the old provider's model due to an operator precedence bug (`selected.available_models.includes(model) || model ? ...`).
  * Removed decommissioned models from Groq (`deepseek-r1-distill-llama-70b` and `mixtral-8x7b-32768`).
  * Fixed hyphenation in Cerebras model IDs (`llama-3.3-70b` and `llama-3.1-8b`, correcting former unhyphenated `llama3.3-70b`).
  * Updated OpenRouter catalogue to point to confirmed `:free` tier models (`meta-llama/llama-3.3-70b-instruct:free`, `openrouter/free`).
  * Synchronized all 8 providers across both frontend `constants.ts` and backend `registry.py`:
    * **Google Gemini:** `gemini-2.0-flash` (default), `gemini-2.0-flash-lite`, `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.5-flash`.
    * **Groq:** `llama-3.3-70b-versatile` (default), `llama-3.1-8b-instant`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`.
    * **Cerebras:** `llama-3.3-70b` (default), `llama-3.1-8b`, `llama-3.1-70b`.
    * **OpenRouter:** `meta-llama/llama-3.3-70b-instruct:free` (default), `meta-llama/llama-3.1-8b-instruct:free`, `google/gemini-2.0-flash-exp:free`, `deepseek/deepseek-r1:free`, `mistralai/mistral-7b-instruct:free`, `openrouter/free`.
    * **NVIDIA NIM:** `meta/llama-3.3-70b-instruct` (default), `meta/llama-3.1-8b-instruct`, `nvidia/llama-3.1-nemotron-70b-instruct`, `mistralai/mistral-large-2-instruct`.
    * **Mistral AI:** `mistral-small-latest` (default), `open-mistral-7b`, `codestral-latest`, `mistral-large-latest`.
    * **OpenAI:** `gpt-4o-mini` (default), `gpt-4o`, `o3-mini`, `gpt-4-turbo`.
    * **Ollama (Local):** `llama3.2` (default), `llama3.3`, `llama3.1`, `qwen2.5`, `mistral`.

---

## 3. Modified Files Summary

| File Path | Description of Change |
| :--- | :--- |
| [`frontend/app/globals.css`](frontend/app/globals.css) | Added explicit `[data-theme='light']` and `[data-theme='dark']` token mappings and smooth color transitions. |
| [`frontend/app/layout.tsx`](frontend/app/layout.tsx) | Added zero-flash theme initialization script and `suppressHydrationWarning`. |
| [`frontend/app/settings/page.tsx`](frontend/app/settings/page.tsx) | Fixed model reconciliation bug on provider switch, added fallback banners, URL validation, and save button animation states. |
| [`frontend/components/app-shell.tsx`](frontend/app/shell.tsx) | Added theme toggle button and state synchronization. |
| [`frontend/components/job-card.tsx`](frontend/components/job-card.tsx) | Added client-side HTML tag sanitization to prevent raw tags from displaying in job descriptions. |
| [`frontend/components/source-form.tsx`](frontend/components/source-form.tsx) | Added non-blocking offline metadata fallback notice. |
| [`frontend/lib/storage.ts`](frontend/lib/storage.ts) | Added theme persistence helpers and durable storage capability detection. |
| [`frontend/lib/constants.ts`](frontend/lib/constants.ts) | Synchronized all 8 provider catalogues with active free-tier models and correct IDs. |
| [`backend/app/section1_foundation_and_providers/providers/base.py`](backend/app/section1_foundation_and_providers/providers/base.py) | Hardened JSON object extraction against code fences anywhere, trailing commas, and array roots. |
| [`backend/app/section1_foundation_and_providers/providers/registry.py`](backend/app/section1_foundation_and_providers/providers/registry.py) | Synchronized backend provider model catalogue with frontend updates across all 8 providers. |
| [`backend/app/section3_job_sources/base.py`](backend/app/section3_job_sources/base.py) | Upgraded `strip_html` to decode entities first, strip ATS boilerplates, and format list bullets. |
| [`backend/app/section3_job_sources/adapters/greenhouse.py`](backend/app/section3_job_sources/adapters/greenhouse.py) | Used `company_name` when present. |
| [`backend/app/section3_job_sources/adapters/ashby.py`](backend/app/section3_job_sources/adapters/ashby.py) | Prioritized `descriptionPlain` over `descriptionHtml`. |
| [`backend/app/section3_job_sources/adapters/lever.py`](backend/app/section3_job_sources/adapters/lever.py) | Added guard to ensure `postings_data` is a list before iteration. |
| [`backend/app/section4_ranking_and_search/services/ranking.py`](backend/app/section4_ranking_and_search/services/ranking.py) | Increased job description slice window from 1500 to 3000 chars for LLM calibration. |

---

## 4. Verification & Testing Status

* **Backend Test Suite:** 45/45 pytest unit tests passed successfully (`pytest backend/app`).
* **Frontend Type-Check & Build:** `next build` completed successfully across all static and server-rendered routes with zero errors.
