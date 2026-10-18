# Thank Me Later — Stage 1: Resume-to-Job Matcher

BYOK job matcher: parses your resume, finds the top 20 roles across public job boards, and tailors your resume to each one. Thank me later.

A high-performance, privacy-first web application that matches candidates to job openings across 7 platforms using user-provided LLM keys (BYOK) and hybrid ranking.

Built with **Zero Backend Persistence**: Resumes, parsed profiles, raw text, and API keys are **never** stored on disk, SQLite, Redis, or any database. All processing occurs ephemerally in RAM.

---

## Architecture & Data Flow

```
[Upload PDF/DOCX] (5MB max, in-memory magic bytes & zip-bomb checks, timeout guard)
       │
       ▼
[Delimited LLM Extraction] (Prompt-injection safe <resume_document> tag, auto-experience derivation)
       │
       ▼
[Confirmation Screen] (Review & edit skills, roles, remote preferences, location)
       │
       ▼
[Privacy-Preserving Search] (Sends ONLY minimal SearchProfile; zero raw text or bullets transmitted)
       │
       ▼
[Concurrent Aggregation] (7 sources via asyncio.gather with return_exceptions=True, 10-min cache)
       │
       ▼
[Hybrid Ranking Funnel] (Deduplicate -> 30-day filter -> Heuristic top 100 -> Batched LLM top 30)
       │
       ▼
[Ranked Feed] (Top 20 matches with match reasons, skill badges, and safe rel="noopener noreferrer" links)
```

---

## Security & Privacy Non-Negotiables

1. **Zero Persistence**: No database, no file storage, no disk I/O for resumes or credentials.
2. **BYOK Secret Redaction**: All API keys registered per-request in `contextvars.ContextVar` and scrubbed by `SecretRedactingLoggingFilter` (and regex pattern matcher) from all logs and traces.
3. **Validation Sanitization**: FastAPI `RequestValidationError` handler drops the `"input"` field to prevent reflection of sensitive body payloads or headers.
4. **Outbound Link Sanitization**: Outbound application links strictly enforce HTTP/HTTPS protocols, silently dropping malformed or internal/private IP URLs (`localhost`, `10.x`, `192.168.x`).
5. **Prompt Injection Hardening**: Resume and job texts delimited inside XML tags with explicit instructions for models to ignore embedded directives.
6. **Client Storage**: Defaults to `sessionStorage` (purged on tab close). `localStorage` is optional and gated behind an explicit security warning modal.

---

## Free-Tier & BYOK API Key Links

### LLM Providers
- **Google Gemini**: [Google AI Studio](https://aistudio.google.com/) *(Free tier available)*
- **Groq**: [Groq Console](https://console.groq.com/) *(Ultra-fast free tier)*
- **OpenRouter**: [OpenRouter Keys](https://openrouter.ai/keys) *(Includes free models like `google/gemini-2.0-flash-exp:free`)*
- **NVIDIA NIM**: [NVIDIA Build](https://build.nvidia.com/) *(Free developer credits)*
- **Cerebras**: [Cerebras Cloud](https://cloud.cerebras.ai/) *(High-speed inference)*
- **Mistral AI**: [Mistral Console](https://console.mistral.ai/)
- **Ollama (Local)**: [Ollama](https://ollama.com/) *(100% local, keyless via `http://localhost:11434` or `http://host.docker.internal:11434`)*

### Official / Public Job Sources
- **Remotive**: Public remote jobs API *(Keyless, free)*.
- **Greenhouse / Lever / Ashby**: Public company ATS job boards *(Keyless, uses company slugs)*.
- **JSearch (RapidAPI)**: [RapidAPI JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) *(Free tier available)*.
- **Adzuna**: [Adzuna Developer Portal](https://developer.adzuna.com/) *(Free developer credentials, supports international routing including India `in`, US, UK)*.
- **Jooble**: [Jooble API](https://jooble.org/api/about) *(Free registration)*.

### Example Company Slugs
Enter these slugs in Settings to search specific company boards:
- **Greenhouse**: `gitlab`, `cloudflare`, `brex`, `airbnb`
- **Lever**: `spotify`, `figma`, `netflix`, `attentive`
- **Ashby**: `openai`, `ramp`, `retool`, `linear`

---

## Attribution & Terms Notice

- **Remotive**: Job listings and data from Remotive are provided under the [Remotive Terms of Service](https://remotive.com/legal). *Powered by Remotive.*

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ / 20+
- Docker & Docker Compose *(optional)*

### Option A: Local Development

#### 1. Backend (FastAPI)
```powershell
# From project root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# Start backend server
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be live at `http://localhost:8000/docs`.

#### 2. Frontend (Next.js 14)
```powershell
# In a new terminal
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

### Option B: Docker Compose

```powershell
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Ollama: Automatically reachable inside containers via `http://host.docker.internal:11434/v1`.

---

## Running the Automated Test Suite

The test suite covers sentinel key redaction, validation error sanitization, provider registry safety, upload hardening, all 7 job source adapters, caching, and hybrid ranking.

```powershell
# Run backend pytest suite (41 tests)
.\.venv\Scripts\pytest -v backend
```

```powershell
# Run frontend build check
cd frontend
npm run build
```

---

## License & Privacy

This project is licensed under the MIT License. Resumes, candidate data, and user API keys are never persisted or shared.

