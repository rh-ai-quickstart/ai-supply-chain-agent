# Tech debt — cleanup status

Inventory of unused / leftover items from the Live Dashboard → Impact Simulation migration. **Removable code debt from this list is complete.** Remaining rows are product/ops suggestions (see [suggestions.md](suggestions.md)), not dead code.

---

## Done

1. Playwright Impact Simulation chrome smoke (`test_impact_simulation_ui.py`).
2. Legacy dashboard API removed; Kind verify uses `/api/v1/version` + gen-sim scenarios.
3. `/api/v1/simulations` catalog removed.
4. Orphan CSS, `react.svg`, empty `agents/`, local `tools/`.
5. Dead `pull_request_check.yaml`; duplicate `helm-tests.yml`.
6. Dead symbols (`is_simulation_intent`, Protocols, AgentService `unknown`); chat clients injected; `route_service` / `routeData` removed.
7. Helm chart packaging: stop tracking `helm/charts/*.tgz` (gitignored cache); document `file://` sibling for general-simulation + keep `gpu-values.yaml` for Option B.
8. Unexport noise: map constants / `DEFAULT_GEOJSON_LIMIT` page re-export; `DEFAULT_IMPACT_QUESTION` imported from `presetScenarioIds`.
9. Ingest defaults aligned to `llamastack` (Makefile + `IngestConfig`).
10. [CONTRIBUTING.md](CONTRIBUTING.md) + README contributing / quality pointer.

---

## Explicitly **not** removable (keep)

| Item | Why |
|------|-----|
| General-simulation / chat / KB / scenarios / news | Core SPA path |
| LangChain ingest strategy modules | Documented alternate |
| Bundled `ingestion/knowledge_base/*.txt` | Ingest Job sources |
| `seed-gen-sim-demo.sh` / `seed-opensky-live.sh` | Map data when in-cluster OpenSky is off |
| `/api/v1/version`, `/healthz`, `/readyz` | Ops / probes |
| `infra/prereqs/ocp-gpu-setup/`, `helm/gpu-values.yaml` | Optional GPU / local-model path |
| NetworkPolicy egress (`allowAll: true` default) | Required for demos on default-deny clusters; further scoping is [suggestions.md](suggestions.md) M4 |
| PGVector / Llama Stack / llm-service subcharts | Deploy path |

---

## Deferred (not code debt)

| Item | Tracker |
|------|---------|
| `podman-compose.yml` | suggestions M1 |
| Scoped NetworkPolicy egress / ingress | suggestions M4 |
| Publish general-simulation chart (drop `file://`) | suggestions M10 |
| Narrow Kind CI triggers | suggestions M11 |
| OpenAPI, pre-commit hooks, commit conventions | suggestions L* |
