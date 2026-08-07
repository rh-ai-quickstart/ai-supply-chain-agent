# Suggestions & Improvements: AI Supply Chain Agent

## High Priority

### H1. Add cleanup of empty vector stores on partial failure
If ingestion fails partway through, empty vector stores are left behind. Add a transactional pattern: create vector store, ingest all docs, only mark complete if all succeed; on failure, delete the empty store.

---

## Medium Priority

### M1. Add `podman-compose.yml` for local development
Contributors must spin up OpenShift or Kind to run the full stack. A `podman-compose.yml` with PostgreSQL/pgvector, backend, and frontend would dramatically lower the contribution barrier. See [CONTRIBUTING.md](CONTRIBUTING.md).

### M4. Tighten NetworkPolicy beyond allow-all egress
An egress NetworkPolicy exists (`helm/templates/network-policy-egress.yaml`, `networkPolicy.egress`). Default `allowAll: true` unblocks LiteMaaS/OpenAI/RSS on default-deny namespaces. Consider scoping destinations further and adding ingress default-deny with allow rules for frontend → backend → data-plane services. (Intentionally deferred — changing defaults can break demos.)

### M7. Keep frontend unit coverage current
Impact-oriented panels and hooks already have tests, plus `chatService` / `newsService` unit coverage and CreateScenario / DashboardHeader error/nav cases. Continue covering ChatBar edge cases and any new panels as features land. Playwright chrome smoke (`tests/e2e_ui/test_impact_simulation_ui.py`) targets Impact Simulation; keep aligned if nav/query labels change.

### M10. Publish general-simulation Helm chart
`general-simulation` still uses a `file://` sibling checkout. After a published chart includes api wait/retry fixes, switch `helm/Chart.yaml` to the remote repo and drop the sibling clone from Kind CI.

### M11. Narrow Kind CI workflow triggers
`kind-helm-smoke.yml` fires on push to `main`, `master`, and `development` with broad path filters. Consider PR-only or tighter paths to avoid unnecessary Kind clusters.

---

## Low Priority / Polish

### L1. Strengthen `pgvector` password guidance in values.yaml
Make it obvious that demo defaults must be replaced for non-demo clusters.

### L4. Document commit message conventions
Optional Conventional Commits note in CONTRIBUTING (no hook required).

### L6. Add a `.pre-commit-config.yaml`
Standardize hooks: ruff/mypy (Python), eslint (frontend), helm-lint, yamllint.

### L7. Add OpenAPI documentation for the backend API
Auto-generate API docs from route decorators for frontend developers.
