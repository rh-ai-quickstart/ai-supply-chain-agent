# What to expect after deployment

This guide describes what the AI Supply Chain Agent quickstart deploys on OpenShift and how to use it. For install steps, see the [README](../README.md).

Default namespace and release name: **`supply-chain-dashboard`**.

---

## What is deployed

A Helm install (`supply-chain-dashboard` in `./helm`) brings up the application tier plus AI/data dependencies:

| Component | Role |
|-----------|------|
| **Backend** (`supply-chain-dashboard-backend`) | Flask API on port 5001 — dashboard state, simulations, RAG chat, knowledge-base uploads |
| **Frontend** (`supply-chain-dashboard-frontend`) | React SPA on port 8080 — operator dashboard (standalone Route) |
| **PGVector** (subchart) | PostgreSQL with pgvector; used for LangChain ingest and default chat RAG when no vector store is selected |
| **Llama Stack** (subchart) | LLM and vector-store APIs for chat and ingestion |
| **LLM service** (subchart) | Model serving (e.g. llama-3-2-3b-instruct) backing Llama Stack |
| **Ingest Job** (optional, `ingest.enabled`) | Post-install job that loads bundled `.txt` documents (`ingest.strategy`: **`llamastack`** by default → Llama Stack vector stores; set `langchain` for PGVector) |

OpenShift **Routes** (main Helm release `supply-chain-dashboard`):

- Frontend UI: `supply-chain-dashboard-frontend`
- Backend API: `supply-chain-dashboard-backend`

Check that workloads are up:

```bash
make oc-status
# or
oc get pods,route -n supply-chain-dashboard
```

Wait until backend, frontend, pgvector, and llamastack pods are **Running** and the ingest job (if enabled) has **Completed**. First startup can take several minutes while models pull and Llama Stack becomes ready.

---

## Backend

### What it is

A single **Flask** service that owns business logic for the dashboard and AI features. It talks to:

- **Llama Stack** — chat completions and (optionally) LlamaStack-native vector stores
- **PGVector** — similarity search for RAG when `VectorStoreClient` initializes successfully
- **OpenSky** (where available) — live aircraft positions for map views; falls back to static demo data on errors

Persistent demo data for **simulations** (name/description catalog) is stored in the API container under `/tmp` — suitable for demos, not production durability.

### How to reach it

From your workstation (replace host with your Route):

```bash
oc get route supply-chain-dashboard-backend -n supply-chain-dashboard -o jsonpath='https://{.spec.host}{"\n"}'
curl -s "$(oc get route supply-chain-dashboard-backend -n supply-chain-dashboard -o jsonpath='https://{.spec.host}')/healthz"
```

Expect: `https://supply-chain-dashboard-backend-supply-chain-dashboard.apps.<app>.<cluster_domain>`.

The **frontend** is built with a proxy pointing at this Route (same-origin `/api/*` via nginx in the cluster).

### API surface (interaction model)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/healthz` | Liveness |
| `GET` | `/api/v1/state` | Full dashboard JSON (KPIs, charts, map layers, alerts) |
| `POST` | `/api/v1/trigger-event` | Random disruption on the current map view (`mapView` in body) |
| `POST` | `/api/v1/simulate` | Scenario preset (`scenario`, optional `optimize`) — returns updated state |
| `POST` | `/api/v1/chat` | RAG chat (`input`, `chat_history`, optional `vector_store_id`) |
| `GET` | `/api/v1/vector_stores` | Llama Stack vector stores (chat knowledge-base picker) |
| `GET` / `POST` | `/api/v1/knowledge-bases` | List UI-upload catalog / upload files (multipart) |
| `GET` / `POST` | `/api/v1/simulations` | List or create named simulation records |

**Simulate** scenarios understood by the backend:

- `none` — refresh live-style dashboard
- `port-strike` — elevates lost-sales KPI and port-strike alerts
- `geopolitical` — Suez-style delay messaging and turnover KPI shift

With `optimize: true`, the response includes synthetic **performance** metrics (vLLM vs monolithic latency/token stats) for demo storytelling.

**Chat** behavior:

- Supply-chain guardrails reject off-topic prompts (food, sports, jokes, etc.).
- Route-style questions can return optimization narrative from `RouteService`.
- With a **vector store** selected in the UI: context comes from Llama Stack (`search_vector_store`).
- Otherwise: context comes from **PGVector** similarity search when `VectorStoreClient` initialized; if PGVector is empty (default `llamastack` ingest), chat still runs but with little or no RAG context until you pick a Llama Stack store or re-ingest with `langchain`.

Example (chat):

```bash
API="https://$(oc get route supply-chain-dashboard-backend -n supply-chain-dashboard -o jsonpath='{.spec.host}')"
curl -s -X POST "$API/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d '{"input":"What risks affect trans-Pacific shipping?","chat_history":[]}'
```

Re-run knowledge ingestion without redeploying Helm:

```bash
make ingest
make ingest-logs
```

---

## Frontend (dashboard)

### What it is

A **React + Vite** single-page app served by nginx. It is the operator UI for the quickstart. One deployment, one Route — no cluster-admin required beyond what the main Helm chart needs.

### How to open it

```bash
oc get route supply-chain-dashboard-frontend -n supply-chain-dashboard
```

Open the **https** URL in a browser. The app polls `GET /api/v1/state` every **15 seconds** and merges simulation results immediately when you run a scenario.

### Layout and interactions

**Header**

- Toggle light/dark theme
- Navigate between **Dashboard** and **Knowledge bases** (hash routes `#/` and `#/knowledge-bases`)

**Dashboard view** (main grid)

1. **AI Simulation & Presets** (left)
   - **Enable vLLM & LLM-D** — passes `optimize` to the backend for performance block in the response
   - **Live Dashboard** — `scenario: none`
   - **Port Strike LA** — port-strike simulation
   - **Suez Blockage** — geopolitical simulation
   - **Trigger World Event** — disruption tied to the active map view

2. **Center**
   - **Demand** and **revenue** charts (Chart.js)
   - **System health** — derived from KPIs, alerts, and load/error state
   - **Logistics map** (Leaflet) — switch **Global**, **Regional**, or **Air freight**; markers and counts update from backend map payloads

3. **Alerts** (right) — critical/warning/info lines from the current state

4. **KPI bar** (bottom) — inventory, turnover, lost sales, revenue, etc.

5. **Chat bar** (fixed bottom)
   - Optional **vector store** selector (Llama Stack stores from `GET /api/v1/vector_stores`)
   - Type a question and send (Enter or button); opens an expanded modal for the thread
   - Answers render as markdown; may include completion metadata when the model returns it

**Knowledge bases view**

- Upload a name plus one or more `.txt` files
- Backend ingests into Llama Stack and registers the catalog
- After a successful upload, return to the dashboard and pick the new store in chat if listed

### What to expect behaviorally

- Map and KPIs reflect **simulated** supply-chain operations, not a live ERP feed.
- Until Llama Stack and ingestion finish, chat may work without RAG context or vector-store options may be empty — check backend logs and `make ingest-status`.
- Simulation buttons show **Running simulation...** while waiting; errors appear inline in the panel.

---

## Suggested walkthrough

1. Open the **frontend Route** and confirm KPIs and map load (backend healthy).
2. Run **Port Strike LA** and watch alerts/KPIs change.
3. Ask the chat: *“Summarize current critical alerts.”* (optionally select a vector store after ingest).
4. Open **Knowledge bases**, upload a short `.txt`, then ask a question grounded in that content.

For troubleshooting pods, routes, and ingest jobs, use `make oc-status`, `make ingest-status`, and `make ingest-logs`.
