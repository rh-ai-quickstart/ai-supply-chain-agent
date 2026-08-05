# Suggestions & Improvements: AI Supply Chain Agent

## High Priority

### H1. Add cleanup of empty vector stores on partial failure (Debt H8)
If ingestion fails partway through, empty vector stores are left behind. Add a transactional pattern: create vector store, ingest all docs, only mark complete if all succeed; on failure, delete the empty store.

---

## Medium Priority

### M1. Add `podman-compose.yml` for local development (Debt M22)
Contributors must spin up OpenShift or Kind to run the full stack. A `podman-compose.yml` with PostgreSQL/pgvector, backend, and frontend would dramatically lower the contribution barrier.

### M2. Add `make test` and `make lint` targets (Debt M24)
No one-command way to run all checks. Add Makefile targets:
- `make test` -- runs backend pytest, frontend vitest, and helm-unittest
- `make lint` -- runs ESLint, ruff/flake8, and mypy
- `make pre-commit` -- runs all of the above plus helm lint

### M3. Extract duplicate atomic JSON writes (Debt M3)
Multiple services (`knowledge_bases_store.py`, `simulations_store.py`, etc.) repeat the same temp-file + rename pattern for atomic writes. Extract to a shared `_json_store.py` utility.

### M4. Externalize Kubernetes NetworkPolicies (Debt M26)
No NetworkPolicies exist; any pod in the namespace can reach Postgres and the backend API. Add default-deny with allow rules for frontend -> backend -> pgvector communication.

### M5. Fix naive guardrail keyword matching (Debt M5)
`_GUARDRAIL_KEYWORDS` uses substring matching (`if keyword in lowered`), so "pizza" matches "pizzazz". Use word-boundary matching with `re.search(r'\b' + re.escape(keyword) + r'\b', lowered)`.

### M6. Add error telemetry to OpenSky flight processing (Debt M6)
`except Exception: continue` in flight-processing loops silently swallows all errors. Add structured logging with the exception type and message, or a counter for failed flights per poll cycle.

### M7. Add test coverage for untested frontend components
`LogisticsMapPanel.jsx`, `KnowledgeBasesPage.jsx`, `ChatBar.jsx`, and `ErrorBoundary.jsx` have no `.test.jsx` files. These are substantial components worth covering.

### M8. Pin pytest version in `requirements-dev.txt`
Currently `pytest>=8.0` (minimum version). For reproducible test runs, pin to an exact version like `pytest==8.3.5`.

### M9. Clean up empty `tools/` directory
The `tools/` directory exists but contains no files. Either remove it or populate it with project utility scripts.

### M10. Switch Helm subcharts from vendored .tgz to remote repos
`helm/charts/` contains vendored `*.tgz` bundles. For reproducibility and transparency, source these from chart repositories with pinned versions. If `ai-architecture-charts` subcharts aren't publicly published, this is a documented tradeoff.

### M11. Document CI workflows trigger paths
`kind-helm-smoke.yml` fires on push to `main`, `master`, and `development` with broad file path filters. This may trigger unnecessary Kind clusters. Narrow the triggers to specific changed-file patterns or make it PR-only.

### M12. Add input validation on simulation trigger endpoint
`POST /api/v1/simulate` accepts a scenario name from the request body with no validation that the scenario exists. Add validation against the scenarios registry and return 400 for unknown scenarios.

---

## Low Priority / Polish

### L1. Add `pgvector` default password placeholder warning in values.yaml
The comment still shows `"password"` as the default. Replace with a note that explicitly says "CHANGE THIS" and make the default `${PGVECTOR_PASSWORD}` with a pre-deploy check script.

### L2. Remove dead `chartSetup.js` imports
`chartSetup.js` exports mappers that may be dead code. Audit imports and remove if truly unused, or document why they exist as a public API.

### L3. Add a CONTRIBUTING.md file
Currently no contribution guide. Add one covering:
- Prerequisites (openshift CLI, podman, pnpm, helm)
- Local dev setup (docker-compose or Kind)
- How to run tests (`make test`)
- PR checklist referencing DEBT.md items

### L4. Add commit message conventions
Configure or document a commit message format convention (e.g., Conventional Commits) and optionally add a Husky commit-msg hook.

### L5. Consider moving DEBT.md items into GitHub Issues
The 43 debt items would be more trackable as structured GitHub Issues with labels (`critical`, `high`, `medium`, `security`). This enables assignees, milestones, and sprint planning.

### L6. Add a `.pre-commit-config.yaml`
Standardize pre-commit hooks: black/isort (Python), eslint (frontend), helm-lint, and yamllint. Run automatically before each commit.

### L7. Add OpenAPI/Swagger documentation for the backend API
Add `flask-openapi3` or `flasgger` to auto-generate API docs from route decorators. This makes the API self-documenting for frontend developers.

### L8. Add health check endpoints to all services
Backend has `/api/healthz` but frontend (nginx) and the ingest job could use proper readiness/liveness probes defined in the Helm deployments.
