# AUDIT REPORT — Thank Me Later (thankmelater-three.vercel.app)
**Status: ALL ISSUES RESOLVED AND VERIFIED**
**Audited: 2026-10-19 | Resolved: 2026-10-21**

---

## 1. Mobile Browser / Network Offline: LLM Providers Dropdown Empty
- **Root Cause**: `providers` state in `SettingsPage` was initialized to empty array `[]`. When accessed via mobile browser on Vercel where the local/remote backend was sleeping, offline, or blocked by mixed content / CORS, the fetch to `/settings/providers` failed, leaving the `<select>` dropdown with 0 `<option>` tags, empty Quick Select pills, and a blank model name input.
- **Resolution**:
  - Created [`frontend/lib/constants.ts`](file:///D:/Thank_Me_Later-2/frontend/lib/constants.ts) defining complete offline `DEFAULT_PROVIDERS` (Gemini, Groq, OpenAI, OpenRouter, NVIDIA NIM, Cerebras, Mistral, Ollama) and `DEFAULT_SOURCES`.
  - Initialized `providers` and `settings` with default values (`gemini` / `gemini-2.5-flash`), guaranteeing the dropdown, quick-select pills, and models render immediately without waiting for a backend round-trip.
  - Styled native mobile `<select option>` elements with `text-foreground` and `bg-card` in [`frontend/app/globals.css`](file:///D:/Thank_Me_Later-2/frontend/app/globals.css) so text remains readable on mobile Chrome and iOS Safari in both light and dark themes.

---

## 2. Button Hover Invisibility (Audit Issue #1)
- **Root Cause**: In dark mode, `.button-primary` had `background: hsl(var(--accent))` (white) and `color: hsl(var(--background))` (dark), but had no dark mode `:hover` rule defined. Tailwind's `hover:bg-black/85` took effect on hover, turning the button background black while the text was already black, causing the button to completely disappear against dark container cards.
- **Resolution**:
  - Re-architected `.button-primary` and `.button-secondary` in [`frontend/app/globals.css`](file:///D:/Thank_Me_Later-2/frontend/app/globals.css) using adaptive HSL CSS variables (`--accent`, `--background`, `--card`, `--foreground`).
  - Added dedicated `:hover:not(:disabled)` rules ensuring proper contrast across both light (`hsl(var(--accent) / 0.88)` dark hover) and dark (`hsl(var(--accent) / 0.88)` bright white hover) themes.
  - Buttons ("Save settings", "Continue", "Find matching jobs", "Apply directly") remain clearly visible on hover in all modes.

---

## 3. In-App Browser Blank Screen Discrepancy (Audit Issue #2)
- **Root Cause**: In restricted browser environments (Claude in-app browser, iOS WebViews, private tabs), direct access to `window.localStorage` and `window.sessionStorage` throws a synchronous `SecurityError` / `DOMException: Access is denied for this document`. Direct calls crashed React hydration and produced a blank white screen.
- **Resolution**:
  - Implemented safe storage wrappers with memory fallback (`safeGetItem`, `safeSetItem`, `safeRemoveItem`) in [`frontend/lib/storage.ts`](file:///D:/Thank_Me_Later-2/frontend/lib/storage.ts).
  - Protected all storage access across [`frontend/lib/api.ts`](file:///D:/Thank_Me_Later-2/frontend/lib/api.ts) and [`frontend/app/settings/page.tsx`](file:///D:/Thank_Me_Later-2/frontend/app/settings/page.tsx).

---

## 4. Settings Page Endpoint Mismatch (Audit Issue #3)
- **Root Cause**: The custom API URL input had a placeholder pointing to Render (`https://thank-me-later-backend.onrender.com`), but the actual active endpoint displayed `http://localhost:8000`, causing user confusion. Furthermore, typing in the input did not reactively test connectivity or re-fetch providers.
- **Resolution**:
  - Enhanced the backend configuration section in [`frontend/app/settings/page.tsx`](file:///D:/Thank_Me_Later-2/frontend/app/settings/page.tsx) with a reactive `activeEndpoint` indicator.
  - Added quick 1-click preset buttons for "Render Backend (Cloud)" and "Localhost (8000)", an "Apply endpoint" button, a "Reset default" button, and an interactive "Ping backend" health check button querying `/health`.

---

## 5. Browser Storage Toggle Visibility (Audit Issue #4)
- **Root Cause**: Radio inputs were marked `sr-only` and cards had subtle 3% opacity background variations with no visible radio buttons or checkmarks, making the active selection ambiguous.
- **Resolution**:
  - Added clear circular radio indicators with inner filled dots when selected.
  - Added a distinct "Recommended" pill badge on the Session option and `border-2 border-black dark:border-white` active selection borders.
