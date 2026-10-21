# Audit Report — Thank Me Later

**Review date:** 2026-10-21  
**Review status:** Audit and implementation plan only. No source-code lines were changed and nothing was pushed to GitHub.

## 1. Scope and objective

This audit separates the work into two independently testable areas:

- **Frontend:** Next.js/React UI, settings state, browser storage, API endpoint selection, and light/dark theme behaviour.
- **Backend:** FastAPI settings and provider endpoints, provider validation, outbound provider requests, CORS, secret handling, and job-source metadata.

The requested product change is to keep the current dark appearance while adding a user-selectable light theme. The implementation should use the existing CSS custom-property and Tailwind-token approach rather than adding a new theme dependency.

## 2. Current architecture observed

### Frontend

- Next.js 14 with React 18 and Tailwind CSS 3.
- Shared colour tokens already exist in [`frontend/app/globals.css`](frontend/app/globals.css).
- The stylesheet currently switches tokens through `@media (prefers-color-scheme: dark)`; this follows the operating-system preference but does not provide an explicit in-app Light/Dark control.
- `frontend/app/layout.tsx` currently renders the root `<html>` element without a theme attribute or explicit theme initialisation.
- `AppShell` is the shared navigation and footer surface for the main pages.
- Settings and source metadata have local fallback catalogues so the UI can remain usable if the backend request fails.

### Backend

- FastAPI application entry point: [`backend/app/main.py`](backend/app/main.py).
- Settings routes expose provider metadata, source metadata, and a credential-bearing connection test.
- Provider registry supports Gemini, Groq, OpenAI, OpenRouter, NVIDIA NIM, Cerebras, Mistral, and Ollama.
- Custom provider URLs are currently restricted server-side to Ollama hosts (`localhost`, `127.0.0.1`, and `host.docker.internal`).
- CORS is configured from environment variables and allows the `X-LLM-Key` header through the wildcard header setting.
- Secrets are registered per request and redacted from logs and error responses.

## 3. Frontend findings and plan

### F1. Stored settings can still make the Provider select appear blank

- **Severity:** High
- **Location:** [`frontend/app/settings/page.tsx:75-82`](frontend/app/settings/page.tsx)
- **Observed behaviour:** The initial state uses a valid fallback provider, but the mount effect later applies stored settings without reconciling the stored provider against the active provider list.
- **Failure scenario:** An unknown stored provider ID produces no matching `<option>`, so the controlled native select appears blank and the test request can submit a stale provider.
- **Plan:** Reconcile stored provider and model values against the current catalogue before applying them. If the provider is unknown, select a valid fallback and its default model.

### F2. A successful remote provider response can invalidate the selected provider

- **Severity:** High
- **Location:** [`frontend/app/settings/page.tsx:56-67`](frontend/app/settings/page.tsx)
- **Observed behaviour:** The remote response replaces the fallback list, but the selected provider is not always checked against the replacement list.
- **Failure scenario:** A provider available locally but absent remotely leaves the select without a matching option.
- **Plan:** After every provider-list replacement, verify that the selected provider exists. Otherwise select the first returned provider and its default model.

### F3. Empty models for non-Gemini providers can disable testing

- **Severity:** Medium
- **Location:** [`frontend/lib/storage.ts:68-75`](frontend/lib/storage.ts)
- **Observed behaviour:** Empty stored models are repaired only for Gemini.
- **Failure scenario:** A non-Gemini setting with an empty model reaches the page and keeps the Test connection action unusable.
- **Plan:** Resolve an empty model from the selected provider's default model, with a safe fallback when the provider is unknown.

### F4. Provider and source fallback states are silent

- **Severity:** Medium
- **Locations:** [`frontend/app/settings/page.tsx:49-73`](frontend/app/settings/page.tsx), [`frontend/components/source-form.tsx:19-32`](frontend/components/source-form.tsx)
- **Observed behaviour:** Failed metadata requests silently retain local defaults.
- **Failure scenario:** Users cannot tell whether they are viewing current backend metadata or a possibly stale local catalogue.
- **Plan:** Keep the fallback for availability, but show a non-blocking offline/fallback message and keep the eventual action error specific.

### F5. Restricted-storage fallback can lose data on reload

- **Severity:** Medium
- **Location:** [`frontend/lib/storage.ts:17-47`](frontend/lib/storage.ts)
- **Observed behaviour:** When browser storage is blocked, values are held only in a module-level memory object.
- **Failure scenario:** A reload clears API keys, endpoint settings, and profiles even though the UI previously reported a successful save.
- **Plan:** Clearly label this as session-memory-only when durable storage is unavailable; do not imply that the value survived a reload.

### F6. Custom endpoint activation needs consistent frontend validation

- **Severity:** Medium
- **Location:** [`frontend/app/settings/page.tsx:191-213`](frontend/app/settings/page.tsx)
- **Observed behaviour:** The frontend trims and stores arbitrary endpoint text before activation.
- **Failure scenario:** Invalid or unsupported input becomes the active endpoint and causes confusing network failures.
- **Plan:** Validate the URL before saving it, require an allowed protocol, and display an inline error without changing the active endpoint when validation fails. The backend remains the authoritative security boundary.

### F7. Theme support is system-driven but not user-selectable

- **Severity:** Medium — requested feature
- **Locations:** [`frontend/app/globals.css:5-12`](frontend/app/globals.css), [`frontend/app/globals.css:55-75`](frontend/app/globals.css), [`frontend/app/layout.tsx:1-4`](frontend/app/layout.tsx)
- **Observed behaviour:** Light tokens are defined, and dark tokens are selected through `prefers-color-scheme: dark`. There is no explicit Light/Dark setting, no persisted user override, and no theme control in the shared shell.
- **Failure scenario:** A user who prefers light mode cannot choose it independently of the operating-system setting; a user who prefers dark mode cannot explicitly retain it when the system setting changes.
- **Plan:**
  1. Add a small explicit theme preference with `light` and `dark` values; keep the current dark palette as the dark mode baseline.
  2. Apply the preference to the root HTML element before the page paints to avoid a flash of the wrong theme. If no preference is stored, use `prefers-color-scheme` as the default.
  3. Keep the existing CSS variables as the single colour source. Define both palettes for the same semantic tokens (`background`, `foreground`, `card`, `border`, `muted`, and `accent`) rather than scattering page-specific colours.
  4. Add `color-scheme: light dark` so browser-provided controls and scrollbars can match the active scheme; use `prefers-color-scheme` only for the no-override default.
  5. Add an accessible toggle or two-option control in the shared shell. It must have an accessible name, expose the current choice, work by keyboard and pointer, and update the root theme immediately.
  6. Preserve `prefers-reduced-motion: reduce`; theme changes must not require animation. If a transition is added, it must be optional and disabled for reduced-motion users.
  7. Verify both themes on every shared surface, native form control, provider/source select, buttons, focus indicators, notices, and mobile layouts. Check text and interactive contrast against WCAG 2.1 AA targets.
  8. Do not add `next-themes` or another dependency unless the existing root attribute, local storage, and CSS-token pattern proves insufficient.

### Frontend acceptance checks

- Light mode can be selected regardless of the operating-system preference.
- Dark mode remains visually equivalent to the current dark baseline.
- A reload preserves an explicit user choice when browser storage is available.
- With no saved choice, the UI follows the operating-system preference.
- Theme initialisation does not visibly flash the opposite theme.
- Native selects, inputs, buttons, focus rings, notices, navigation, and footer remain readable in both modes.
- Keyboard users can operate the theme control and identify its current state.
- Reduced-motion users receive no theme animation.
- Existing provider, source, endpoint, and storage fallback behaviour remains functional.

## 4. Backend findings and plan

### B1. Credential-bearing connection tests depend on a client-selected backend endpoint

- **Severity:** High — security
- **Locations:** [`frontend/app/settings/page.tsx:121-133`](frontend/app/settings/page.tsx), [`backend/app/section1_foundation_and_providers/routers/settings.py:33-74`](backend/app/section1_foundation_and_providers/routers/settings.py)
- **Observed behaviour:** The frontend sends `X-LLM-Key` to its currently selected backend endpoint. The backend then uses the request's provider and optional base URL to construct the upstream test.
- **Current mitigation:** The backend registry rejects custom URLs for all providers except Ollama and restricts Ollama to local/container hosts; request secrets are redacted.
- **Remaining failure scenario:** A user can still configure a different backend origin in the frontend and send a credential-bearing request there. A trusted backend cannot control which origin the user deliberately selected in a browser UI.
- **Plan:** Make the trust boundary explicit in the UI, validate endpoint activation before use, keep credential-bearing tests separate from health checks, and document that custom backend origins receive the supplied credential. Retain backend-side provider and custom-URL validation as the enforcement boundary.

### B2. Backend provider and model validation should remain authoritative

- **Severity:** High
- **Locations:** [`backend/app/section1_foundation_and_providers/providers/registry.py:142-185`](backend/app/section1_foundation_and_providers/providers/registry.py), [`backend/app/section1_foundation_and_providers/providers/registry.py:217-261`](backend/app/section1_foundation_and_providers/providers/registry.py)
- **Observed behaviour:** Model names are constrained by a safe character pattern, provider IDs come from a registry, and custom URL rules are applied before an outbound request.
- **Plan:** Preserve these checks while adding frontend reconciliation; never treat the frontend catalogue as a security control. Add or retain tests for unsupported providers, invalid models, disallowed custom hosts, missing required keys, and allowed Ollama hosts.

### B3. CORS and secret handling require deployment verification

- **Severity:** Medium
- **Locations:** [`backend/app/main.py:42-70`](backend/app/main.py), [`backend/app/section1_foundation_and_providers/security/security.py:26-59`](backend/app/section1_foundation_and_providers/security/security.py)
- **Observed behaviour:** CORS origins and the Vercel regex are environment-controlled; `X-LLM-Key` is registered for redaction.
- **Plan:** Verify production `ALLOWED_ORIGINS` and `CORS_ORIGIN_REGEX` values, reject unintended origins, and confirm that invalid requests and upstream failures do not echo credentials or sensitive request fields.

### B4. Source metadata has two representations

- **Severity:** Low
- **Locations:** [`backend/app/section3_job_sources/registry.py:21-149`](backend/app/section3_job_sources/registry.py), [`frontend/lib/constants.ts:105-180`](frontend/lib/constants.ts)
- **Observed behaviour:** The frontend maintains a local source fallback while the backend owns the live source metadata.
- **Plan:** Keep the fallback for offline usability, but display its status and test that the fallback shape remains compatible with the backend response.

### Backend acceptance checks

- Unsupported provider IDs and unsafe model names are rejected without secret leakage.
- Non-Ollama custom URLs remain rejected; permitted Ollama hosts continue to work.
- CORS permits only configured frontend origins and expected deployment origins.
- Health checks do not require an API key.
- Credential-bearing tests never include secrets in response bodies, validation errors, or logs.
- One failing job source does not prevent other source results from being returned.

## 5. Implementation order

1. **Frontend state correctness:** reconcile stored and remote provider/model state.
2. **Frontend endpoint and fallback messaging:** validate endpoint input and expose fallback/storage limitations.
3. **Frontend themes:** add explicit Light/Dark selection, root initialisation, semantic tokens, accessibility checks, and persistence.
4. **Backend security verification:** preserve and test provider, model, URL, CORS, and secret boundaries.
5. **Cross-layer verification:** test frontend fallback behaviour against backend metadata and verify both themes across responsive layouts.

## 6. Theme research sources

- [MDN — `prefers-color-scheme`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-color-scheme): use the operating-system preference as the default when the user has not chosen an override.
- [MDN — `color-scheme`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/color-scheme): allow browser-provided controls, scrollbars, and other UI chrome to follow the active scheme.
- [MDN — `light-dark()`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/color_value/light-dark): optional modern CSS shorthand for paired light and dark colour values; use only where the project's browser support target permits it.
- [web.dev — Improve dark mode with `color-scheme` and a meta tag](https://web.dev/articles/color-scheme): recommends declaring supported schemes early and combining `color-scheme` with explicit theme styling.
- [web.dev — `prefers-color-scheme`](https://web.dev/articles/prefers-color-scheme): background on system preference support and dark mode as an accessibility option.

## 7. Constraints and verification record

- Do not edit source code as part of this audit rewrite.
- Do not add dependencies as part of this audit rewrite.
- Do not push to GitHub.
- This document is a plan for a later implementation; no frontend or backend fixes have been applied here.
- The working tree already contained changes to this audit document before this rewrite; those document changes were preserved in the updated report.
