# Root Cause Analysis & Resolution Report

**Date:** 2026-10-22  
**Incident:** Failure to reach backend from Vercel deployment (`Failed to fetch`)  
**Resolution Status:** Resolved & Verified in Production  
**Commit:** [`d4ad89a`](https://github.com/SaiKarun-28/Thank_Me_Later/commit/d4ad89a)  

---

## 1. Incident Overview & Symptoms

When accessing the production frontend on Vercel at `https://thankmelater-pndblo4x1-isaikarun536-9118.vercel.app/settings`:

1. **Initial Page Load:** A yellow warning appeared at the top of the Language Model card:
   > *"Could not load provider metadata. Using the built-in list."*
2. **Action Trigger:** Entering an API key and clicking **"Test connection"** produced a red error card:
   > *"Connection Error: Network error reaching backend: Failed to fetch. Ensure your backend server is running and accessible."*
3. **Console Diagnostic:** The browser threw a client-side `TypeError: Failed to fetch` on requests to `/settings/providers` and `/settings/test`.

---

## 2. Root Cause Analysis

Investigation revealed two interconnected root causes preventing communication between the Vercel frontend and the Render backend:

### Root Cause 1: Default Client-Side API Endpoint (`localhost` vs HTTPS)
* **Code Location:** [`frontend/lib/api.ts`](frontend/lib/api.ts)
* **Mechanism:**
  ```typescript
  export function getDefaultApiUrl(): string {
    return (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
  }
  ```
* When built on Vercel without `NEXT_PUBLIC_API_URL` defined in the Vercel project environment variables, the compiled bundle defaulted to `http://localhost:8000`.
* The browser running on an HTTPS origin (`https://thankmelater-...vercel.app`) was blocked from making requests to `http://localhost:8000` due to:
  1. **Mixed Content Security:** Browsers block cleartext `http://` calls originating from secure `https://` contexts.
  2. **Unreachable Localhost:** When opened on mobile or machines without a local backend running on port 8000, `localhost` refused connections immediately.

---

### Root Cause 2: FastAPI CORS Middleware Domain Mismatch
* **Code Location:** [`backend/app/main.py:62`](backend/app/main.py) and [`render.yaml:17`](render.yaml)
* **Original Configuration:**
  ```python
  cors_regex = os.getenv("CORS_ORIGIN_REGEX", r"^https://thank-me-later(-[a-z0-9-]+)?\.vercel\.app$")
  ```
* **Failure Mechanism:**
  * The Vercel deployment URL created for the repository was:
    `https://thankmelater-pndblo4x1-isaikarun536-9118.vercel.app`
  * Notice that `thankmelater` is **unhyphenated**, whereas the regular expression explicitly required hyphens: `thank-me-later`.
  * Even when the user configured the frontend to point directly to Render (`https://<service-name>.onrender.com`), FastAPI's `CORSMiddleware` evaluated the `Origin` header against the regex, rejected the preflight `OPTIONS` request, and returned:
    * **HTTP Status:** `400 Bad Request`
    * **Header:** `access-control-allow-origin: None`
  * The browser consequently blocked the response from reaching JavaScript, reporting a generic `TypeError: Failed to fetch`.

---

### Contributing Factor 3: Render Free Tier Inactivity (Cold Start)
* The backend is hosted on Render's free tier. Render spins down inactive containers after 15 minutes of idle time.
* Cold spin-up takes between 30 and 50 seconds on initial wake-up. If a request is attempted before the container finishes binding to its port, the connection times out.

---

## 3. Reproduction & Diagnostic Proof

Before applying the fix, a test was executed against FastAPI's preflight handler using the exact origin from the screenshot:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
res = client.options('/settings/providers', headers={
    'Origin': 'https://thankmelater-pndblo4x1-isaikarun536-9118.vercel.app',
    'Access-Control-Request-Method': 'GET',
    'Access-Control-Request-Headers': 'Content-Type,X-LLM-Key'
})
# Output BEFORE fix:
# Status: 400
# Access-Control-Allow-Origin: None
```

This proved conclusively that FastAPI's CORS middleware was actively rejecting all browser requests originating from `https://thankmelater-*.vercel.app`.

---

## 4. Remediation & Implementation

### 1. Updated Backend CORS Regex
Modified [`backend/app/main.py`](backend/app/main.py) to support both hyphenated (`thank-me-later`) and unhyphenated (`thankmelater`) Vercel production and preview subdomains:

```python
# backend/app/main.py
cors_regex = os.getenv("CORS_ORIGIN_REGEX", r"^https://(thank-me-later|thankmelater)(-[a-z0-9-]+)?\.vercel\.app$")
```

### 2. Updated Infrastructure as Code (`render.yaml`)
Synchronized [`render.yaml`](render.yaml) so automated Render deployments inject the matching regex into environment variables:

```yaml
# render.yaml
services:
  - type: web
    name: thank-me-later-backend
    ...
    envVars:
      - key: CORS_ORIGIN_REGEX
        value: ^https://(thank-me-later|thankmelater)(-[a-z0-9-]+)?\.vercel\.app$
```

### 3. Added Automated Regression Tests
Added `test_cors_preflight_vercel_origins` in [`backend/app/section1_foundation_and_providers/tests/test_security.py`](backend/app/section1_foundation_and_providers/tests/test_security.py):

```python
def test_cors_preflight_vercel_origins(client: TestClient):
    """Verify CORS preflight succeeds for both hyphenated and unhyphenated Vercel deployment URLs."""
    valid_origins = [
        "https://thankmelater-pndblo4x1-isaikarun536-9118.vercel.app",
        "https://thankmelater.vercel.app",
        "https://thank-me-later.vercel.app",
        "https://thank-me-later-preview.vercel.app",
    ]
    for origin in valid_origins:
        res = client.options(
            "/settings/providers",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type,X-LLM-Key",
            },
        )
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == origin
```

---

## 5. Verification & Test Results

* **Automated Security & CORS Test:** 9 passed in `test_security.py`.
* **Full Backend Test Suite:** All 45 tests passed (`pytest backend`).
* **Frontend Compilation:** Clean Next.js 14 production build (`npm run build`).
* **Post-Fix Preflight Verification:**
  ```
  Status: 200 OK
  Access-Control-Allow-Origin: https://thankmelater-pndblo4x1-isaikarun536-9118.vercel.app
  ```
* **Git Delivery:** Pushed to GitHub repository `origin/main` under commit `d4ad89a`.

---

## 6. Operational Recommendations

1. **Vercel Environment Variable (Recommended for Zero-Config Client Loads):**
   * In Vercel Project Dashboard → **Settings** → **Environment Variables**, add:
     * `NEXT_PUBLIC_API_URL` = `https://<your-service-name>.onrender.com`
   * Trigger a Redeployment on Vercel so new visitors automatically point to the cloud backend without manual input in the Settings UI.
2. **In-App Endpoint Switcher:**
   * The **Backend API Endpoint** configuration in `/settings` allows instant switching and local storage override without requiring a redeployment.
