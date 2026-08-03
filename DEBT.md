# Technical Debt & Improvement Backlog

Categorized list of issues to address across the codebase. Each item includes file paths and line
numbers for quick navigation.  Work through them in any order — pick what interests you.

---

## 🔴 Critical

- [x] **C1 — `bool(payload.get("optimize", False))` treats `"false"` as `True`**
      `app/backend/api/main.py:76` — Fixed. Now uses
      `payload.get("optimize", False) in (True, "true", 1, "1")`.

- [x] **C2 — `LLAMA_STACK_OPENAI_MODEL` raises `KeyError` if unset**
      `app/backend/api/main.py:45` — Fixed. Changed to `os.getenv(...)` with a fallback and a
      clear log message.

- [x] **C3 — Chart.js registration file never imported**
      `app/frontend/src/lib/chartSetup.js` — Fixed. Imported in `main.jsx`.

- [x] **C4 — No React error boundary anywhere**
      `app/frontend/src/App.jsx` — Fixed. Added `<ErrorBoundary>` component wrapping the app
      shell (`app/frontend/src/components/ErrorBoundary.jsx`).

- [ ] **C5 — No `package-lock.json` committed**
      `app/frontend/` — `npm ci` used in CI requires a lockfile.  Generate and commit one, or
      switch CI to `npm install`.

- [x] **C6 — API and ingestion use different embedding endpoints**
      `app/backend/api/clients/vector_store_client.py:33` uses
      `{llama_stack_url}/v1/openai/v1` while
      `app/backend/ingestion/clients/vector_store_client.py:33` uses `{llama_stack_url}/v1`.
      One of these is wrong — verify and align them.
      Aligned both to `{llama_stack_url}/v1` (the OpenAI-SDK base URL for Llama Stack on
      OpenShift AI 3.4; embeddings are served at `/v1/embeddings`).

---

## 🟠 High

### Backend

- [x] **H1 — Python requirements unpinned**
      `app/backend/api/requirements.txt` and `app/backend/ingestion/requirements.txt` — Done.
      Pinned to exact versions from the current working environment.

- [x] **H2 — Flask debug mode enables Werkzeug debugger (RCE vector)**
      `app/backend/api/main.py:180` — Fixed. Now driven by `FLASK_DEBUG` env var
      (`"1"`, `"true"`, `"yes"`), defaults to `False`.

- [ ] **H3 — 23 bare `except Exception` handlers**
      Spread across every backend service file.  These mask `AttributeError`, `TypeError`,
      `KeyError`, etc.  Narrow exception types or at minimum log the full traceback.

- [x] **H4 — No SecurityContext on Helm workloads**
      `helm/templates/backend-deployment.yaml`, `frontend-deployment.yaml`, `ingest-job.yaml` —
      All three workloads now have `securityContext` at the pod and container level with
      `runAsNonRoot: true`, `seccompProfile: RuntimeDefault`, `allowPrivilegeEscalation: false`,
      and `capabilities.drop: [ALL]`.

- [x] **H5 — Containerfiles run as root**
      `app/backend/api/Containerfile` and `app/backend/ingestion/Containerfile` — Both now add
      `appuser` via `useradd -m appuser && chown appuser:0 /app && chmod g+rwX /app && USER appuser`.
      Also OpenShift-compatible with group-0 permissions.

- [x] **H6 — Default PG password `"password"` hardcoded**
      `app/backend/api/clients/vector_store_client.py:19` — Both API and ingestion clients now
      raise `RuntimeError` if `PG_PASSWORD` is unset, instead of silently falling back to
      `"password"`.

- [ ] **H7 — Ingestion creates one vector store per file**
      `app/backend/ingestion/services/llamastack_ingestion_service.py:57-62` — A directory with
      100 files creates 100 separate vector stores.  Batch files into a single store per directory.

- [ ] **H8 — No cleanup of empty vector stores on partial upload failure**
      `app/backend/api/services/knowledge_base_ingest_service.py:63-86` — If vector store
      creation succeeds but all subsequent file uploads fail, the empty store is leaked.  Add
      a cleanup step.

### Frontend

- [x] **H9 — No PropTypes or TypeScript on any component**
      All 12 components in `app/frontend/src/components/` — Added `prop-types` package and
      `propTypes` + default values on every component.

- [x] **H10 — `SimulationPanel.jsx` has zero tests**
      `app/frontend/src/components/SimulationPanel.jsx` — 7 tests added covering rendering,
      interaction and edge cases.

- [x] **H11 — `SystemHealthPanel` crashes if `health` prop is missing**
      `app/frontend/src/components/SystemHealthPanel.jsx:17-26` — Fixed. Added
      `const health = _health ?? {}` guard at the top of the component.

- [x] **H12 — Chart components crash on null/undefined `data` prop**
      `app/frontend/src/components/DemandChartPanel.jsx` and
      `app/frontend/src/components/RevenueChartPanel.jsx` — Both now render a
      `"No <...> data available."` fallback when `!data`.

### Infrastructure

- [ ] **H13 — API has no authentication on any endpoint**
      `app/backend/api/main.py` — `/api/v1/state`, `/api/v1/chat`, `/api/v1/simulate`,
      `/api/v1/knowledge-bases` are fully unauthenticated.  Add at minimum a shared API key
      check for production deployments.

- [ ] **H14 — No container or dependency vulnerability scanning in CI**
      No Dependabot, Trivy, or `pip-audit` integration.  Images are built and pushed without
      any CVE gate.

---

## 🟡 Medium

### Backend

- [x] **M1 — `_sse_event` has no escaping for `\n\n` in answer text**
      `app/backend/api/main.py` — Escaped: `text.replace("\n\n", "\n")` before wrapping in
      SSE `data:` frame.

- [ ] **M2 — No rate limiting on any endpoint**
      `app/backend/api/main.py` — `/api/v1/chat`, `/api/v1/simulate`, `/api/v1/knowledge-bases`
      POST have no rate limits.  Chat in particular creates LLM API cost exposure.  Add
      `flask-limiter` or a simple in-memory token bucket.

- [ ] **M3 — Duplicate atomic JSON-write code**
      `app/backend/api/services/knowledge_bases_store.py` and
      `app/backend/api/services/simulations_store.py` — The tmp-file + `os.replace` pattern is
      identical.  Extract into `app/backend/api/services/_json_store.py` shared helper.

- [ ] **M4 — `SupplyChainStateBuilder` has ~180 lines of hardcoded data**
      `app/backend/api/services/supply_chain_state_builder.py` — Port coordinates, routes, and
      assets are hardcoded in `_sea_freight_data()` and `_land_freight_data()`.  Move to JSON
      or YAML config files.

- [ ] **M5 — Guardrail keyword matching is naive substring check**
      `app/backend/api/services/chat_service.py:114` — `any(keyword in lowered for ...)` matches
      substrings, so "pizza" also matches "pizzazz".  Use word-boundary matching or a small
      ML classifier.

- [ ] **M6 — `get_live_air_state` silently skips errors per-flight**
      `app/backend/api/services/supply_chain_state_builder.py:235-236, 265-266` —
      `except Exception: continue` inside the flight-processing loop.  If the OpenSky API
      changes its response format, every flight silently fails and the UI shows nothing.
      At minimum, log a warning on the first failure.

- [x] **M7 — `ingest_uploaded_files` slug length 48 is a magic number**
      `app/backend/api/services/knowledge_base_ingest_service.py` — Extracted to
      `_MAX_VECTOR_STORE_NAME_LENGTH = 48` with a doc comment explaining LlamaStack's limit.

- [ ] **M8 — `connect_to_llamastack_client` contains dead code**
      `app/backend/api/services/knowledge_base_manager.py:16-24` — The inner `if self._llama_client
      is None` check is unreachable because the caller already guarantees it.  Simplify or remove.

- [ ] **M9 — Simulation scenarios (`port-strike`, `geopolitical`) hardcoded with inline KPI mutations**
      `app/backend/api/services/dashboard_service.py:65-86` — Adding a new scenario requires
      code changes.  Consider making scenario definitions data-driven (JSON config or DB table).

- [x] **M10 — Missing `__init__.py` in `api/` package**
      `app/backend/api/__init__.py` — Fixed. Empty `__init__.py` added.

### Frontend

- [x] **M11 — `setTimeout` in ChatBar never cleaned up on unmount**
      `app/frontend/src/components/ChatBar.jsx:42-46` — Fixed. Timer ID is now captured and
      cleared via the effect cleanup function.

- [x] **M12 — `reloadVectorStores` has no cancellation on unmount**
      `app/frontend/src/App.jsx` — Fixed. Uses `AbortController` passed through `apiGet`,
      with `signal?.aborted` guards on state updates.

- [x] **M13 — `useDashboardState` polling races with itself**
      `app/frontend/src/hooks/useDashboardState.js` — Fixed. Uses a generation counter:
      `++gen` before each fetch, discards stale responses where `myGen !== gen`.

- [ ] **M14 — Map assets use `index` in React `key`**
      `app/frontend/src/components/LogisticsMapPanel.jsx:56` — Currently `asset.id` is the
      primary key with `name-index` as fallback.  Acceptable for now as assets always carry IDs
      from the backend.

- [x] **M15 — `LogisticsMapPanel` re-creates `MapContainer` on every render**
      `app/frontend/src/components/LogisticsMapPanel.jsx` — Wrapped component in `React.memo`
      so the `MapContainer` tree is only re-rendered when its actual props change.

- [ ] **M16 — Unsafe HTML interpolation in Leaflet `divIcon`**
      All interpolated values (`asset.track`, `colors.fill`) are internally-controlled numbers
      or hardcoded strings — no user-input vector.  Marked low-risk / no-fix.

- [ ] **M17 — Dead exports: `chartSetup.js`, `toDemandChartData`, `toRevenueChartData`, `toSystemHealthMetrics`**
      `chartSetup.js` is imported in `main.jsx`.  The three mapper functions have full test
      coverage and represent a public API.  Keeping them.

- [x] **M18 — Theme toggle has no accessible label**
      `app/frontend/src/components/DashboardHeader.jsx:25-27` — Fixed. Added
      `aria-label="Toggle theme"`.

- [x] **M19 — `AlertsPanel` crashes if `alerts` prop is `undefined`**
      `app/frontend/src/components/AlertsPanel.jsx` — Fixed. Added `alerts = []` default in
      destructured props.

- [x] **M20 — Map view `<select>` has no associated `<label>`**
      `app/frontend/src/components/LogisticsMapPanel.jsx:14` — Fixed. Added
      `<label htmlFor="map-view-select" className="sr-only">` with corresponding `id` on the
      `<select>`.  Added `.sr-only` CSS class to `index.css`.

- [ ] **M21 — Hardcoded error messages in 8+ places**
      `App.jsx`, `useDashboardState.js`, `KnowledgeBasesPage.jsx` — Error message strings are
      duplicated across files.  Centralize in a constants file.

### Infrastructure

- [ ] **M22 — No `docker-compose.yml` for local development**
      Developers need OpenShift or Kind to run the full stack.  A `compose.yml` with Postgres
      + backend + frontend would lower the contribution barrier significantly.

- [x] **M23 — `.gitignore` missing `.env`, `.pytest_cache`, `.cursor/`**
      `.gitignore` — Fixed. Added `.env`, `.env.*`, `.pytest_cache/`, and `.cursor/` entries.

- [ ] **M24 — No `test` or `lint` target in Makefile**
      `make test` should run backend + frontend + Helm tests.  `make lint` should run
      `ruff`, `eslint`, `yamllint`.  Currently only `make helm-lint` exists.

- [x] **M25 — `CORS(app)` allows all origins**
      `app/backend/api/main.py:22` — Default CORS removed.  Now only enabled when
      `CORS_ORIGIN` env var is set (for dev with separate frontend origin).

- [ ] **M26 — No `NetworkPolicy` in Helm templates**
      Any pod in the namespace can reach Postgres, Llama Stack, and the backend API.  Add
      a `NetworkPolicy` that locks down ingress/egress per component.

- [x] **M27 — Helm chart is named `example`**
      `helm/Chart.yaml:2` — Renamed to `supply-chain-agent` with updated description.

---

## 🟢 Quick Wins (< 5 minutes each)

- [x] **Q1** — `bool(payload.get("optimize", False))` → use a proper truthy check (`main.py:76`)
- [x] **Q2** — `os.environ["LLAMA_STACK_OPENAI_MODEL"]` → `os.getenv(...)` (`main.py:45`)
- [x] **Q3** — Import `chartSetup.js` in `main.jsx` to fix Chart.js registration
- [x] **Q4** — Add `USER 1001` to both Python Containerfiles
- [x] **Q5** — Add `package-lock.json` to `.gitignore` or commit one
- [x] **Q6** — Add null guard in `SystemHealthPanel`: `const h = health ?? {}`
- [x] **Q7** — Add `setTimeout` cleanup in `ChatBar`: `const t = setTimeout(...); return () => clearTimeout(t)`
- [x] **Q8** — Add `aria-label="Toggle theme"` to theme toggle button
- [x] **Q9** — Pin Python requirements with exact versions
- [x] **Q10** — Add `.env`, `.pytest_cache`, `.cursor/` to `.gitignore`
- [x] **Q11** — Add `alerts = []` default to `AlertsPanel` destructured props
- [x] **Q12** — Add `<label htmlFor="map-view-select">` to `LogisticsMapPanel`
- [x] **Q13** — Remove `void` operator from async calls in `App.jsx:67` and `KnowledgeBasesPage.jsx:28`
- [x] **Q14** — Remove `App.css` import (it's dead boilerplate CSS)
- [x] **Q15** — Add `api/__init__.py` so `from api import main` works
