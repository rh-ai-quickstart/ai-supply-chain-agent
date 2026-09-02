# UI E2E tests (Playwright)

Browser tests for the supply chain dashboard React app. Based on the [RAG](https://github.com/rh-aiservices-bu/RAG) quickstart `tests/e2e_ui/` layout.

## Setup

```bash
make e2e-ui-install
```

## Run

Against a Kind deployment (after `make helm-install-kind` and port-forwards):

```bash
# Terminal 1 — or use make kind-verify-e2e (curl + UI in one script)
export SUPPLY_CHAIN_UI_ENDPOINT=http://127.0.0.1:18080
export BACKEND_HEALTH_URL=http://127.0.0.1:15001/healthz
make e2e-ui
```

Against Vite dev server:

```bash
export SUPPLY_CHAIN_UI_ENDPOINT=http://localhost:5173
export BACKEND_HEALTH_URL=http://127.0.0.1:5001/healthz
make e2e-ui
```

### Debug (visible browser)

```bash
pytest tests/e2e_ui/ -v --headed --slowmo 500 --browser chromium
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPPLY_CHAIN_UI_ENDPOINT` | `http://127.0.0.1:18080` | Frontend base URL |
| `BACKEND_HEALTH_URL` | `http://127.0.0.1:15001/healthz` | Backend liveness (session fixture) |
| `SKIP_MODEL_TESTS` | `false` | Set `true` to skip chat tests that call the LLM |
| `E2E_CHAT_TIMEOUT_MS` | `120000` | Max wait for chat replies |

## Test files

| File | Coverage |
|------|----------|
| `test_impact_simulation_ui.py` | Header, Simulation / KB nav, scenario panel, suggested prompts, Create scenario modal, All Flights default, chat input |
| `test_chat_ui.py` | Off-topic guardrail |
| `test_knowledge_bases_ui.py` | Nav + `#/knowledge-bases` hash route |

Current SPA routes: `#/simulation`, `#/knowledge-bases`. Prefer unit tests under `app/frontend/src/**/*.test.*` for map/results deep coverage; this suite is chrome + chat smoke for Kind.

When `RUN_UI_E2E=1`, `scripts/ci/kind-verify-deployment.sh` seeds the three preset demo scenarios directly in Neo4j (`scripts/ci/kind-seed-demo-scenarios.py` via `general-sim-api`) before Playwright runs. This avoids the admin inject API, which requires Llama Stack (disabled on Kind).
