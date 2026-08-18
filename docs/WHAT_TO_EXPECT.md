# What to expect after deployment

This guide describes what the AI Supply Chain Agent quickstart deploys on OpenShift and how to use it. For install steps, see the [README](../README.md).

Default namespace and release name: **`supply-chain-dashboard`**.

---

## What is deployed

A Helm install (`supply-chain-dashboard` in `./helm`) brings up the application tier plus AI/data dependencies:

| Component | Role |
|-----------|------|
| **Backend** (`supply-chain-dashboard-backend`) | Flask API on port 5001 — impact simulation proxy, RAG chat, knowledge-base uploads, scenario create |
| **Frontend** (`supply-chain-dashboard-frontend`) | React SPA on port 8080 — impact workspace (standalone Route) |
| **General Simulation** (subchart, enabled by default) | Impact engine (API + Neo4j + Postgres) for scenarios, GeoJSON entities, and NL impact queries |
| **Shared Postgres** (gen-sim subchart) | PostgreSQL with AGE + pgvector + PostGIS; agent RAG and gen-sim share one Postgres instance |
| **Llama Stack** (gen-sim subchart) | LLM and vector-store APIs for chat and ingestion |
| **LLM service** (gen-sim subchart) | In-cluster vLLM; model id from `general-simulation.api.models.generation` |
| **Ingest Job** (optional, `ingest.enabled`) | Post-install job that loads bundled risk documents (`ingest.strategy`: **`llamastack`** by default → Llama Stack vector stores; set `langchain` for PGVector) |

OpenShift **Routes** (main Helm release `supply-chain-dashboard`):

- Frontend UI: `supply-chain-dashboard-frontend`
- Backend API: `supply-chain-dashboard-backend`

Check that workloads are up:

```bash
make oc-status
# or
oc get pods,route -n supply-chain-dashboard
```

Wait until backend, frontend, llamastack, gen-sim Postgres, and general-simulation pods are **Running** and the ingest job (if enabled) has **Completed**. First startup can take several minutes while Llama Stack becomes ready (and longer if you enable a local model).

### Map / OpenSky data (important)

The Impact Map and **Live Flights** UI read **seeded PostGIS geometries** from general-simulation — not live calls from the backend to OpenSky.

- In-cluster OpenSky ingestion is **disabled** by default (`general-simulation.ingestion.enabled: false`). OpenSky often blocks AWS/hyperscaler source IPs (TCP timeout); cluster NetworkPolicy/EgressFirewall cannot override that.
- After deploy, seed demo scenarios and maritime data from your laptop:

```bash
make seed-gen-sim
# optional: many live aircraft via laptop egress (OpenSky reachable from your machine)
make seed-opensky-live GEN_SIM_NAMESPACE=supply-chain-dashboard
# or both:
make seed
```

Requires a local checkout of [general-simulation](https://github.com/robertsandoval/general-simulation) (sibling directory by default: `../general-simulation`) and `oc` login.

---

## Backend

### What it is

A single **Flask** service that owns business logic for the dashboard and AI features. It talks to:

- **Llama Stack** — chat completions and (optionally) LlamaStack-native vector stores
- **PGVector** — similarity search for RAG when `VectorStoreClient` initializes successfully
- **General Simulation** — impact queries, scenario list, entity GeoJSON (`GENERAL_SIMULATION_BASE_URL`)
- **RSS news** — headlines for the ticker (`GET /api/v1/news`); needs HTTPS egress

Persistent demo data for knowledge-base catalog metadata is stored in the API container under `/tmp` — suitable for demos, not production durability.

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
| `GET` | `/readyz` | Readiness (Llama Stack / gen-sim / PGVector checks) |
| `GET` | `/api/v1/version` | Build commit / timestamp |
| `GET` | `/api/v1/general-simulation/scenarios` | Scenario IDs for the picker |
| `POST` | `/api/v1/general-simulation/query` | Natural-language impact query (`question`, `scenario_id`) |
| `GET` | `/api/v1/general-simulation/entities/geojson` | Map features (bbox / scenario filters) |
| `POST` | `/api/v1/chat` | RAG chat (`input`, `chat_history`, optional `vector_store_id`; UI uses SSE streaming) |
| `GET` | `/api/v1/vector_stores` | Llama Stack vector stores (chat knowledge-base picker) |
| `GET` / `POST` | `/api/v1/knowledge-bases` | List UI-upload catalog / upload files (multipart) |
| `POST` | `/api/v1/scenarios/propose` | Draft a scenario from a natural-language prompt |
| `POST` | `/api/v1/scenarios` | Create a scenario in general-simulation |
| `GET` | `/api/v1/news` | Supply-chain-relevant RSS headlines |

**Primary UI path:** pick a seeded scenario → `POST .../general-simulation/query` → map GeoJSON + impact results.

**Chat** behavior:

- Supply-chain guardrails reject off-topic prompts (food, sports, jokes, etc.).
- With a **vector store** selected (UI auto-matches by scenario keywords): context comes from Llama Stack (`search_vector_store`).
- Otherwise: context comes from **PGVector** similarity search when `VectorStoreClient` initialized; if PGVector is empty (default `llamastack` ingest), chat still runs but with little or no RAG context until you pick a Llama Stack store or re-ingest with `langchain`.
- Chat can also invoke tools (general-simulation query, news, knowledge base) depending on the prompt.

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

Open the **https** URL in a browser. Use **Simulation** (`#/simulation`) for the map and impact queries. Seed map data with `make seed-gen-sim` (and optionally `make seed-opensky-live`) against the dashboard namespace before expecting markers.

### Layout and interactions

**Header**

- Toggle light/dark theme
- Navigate between **Simulation** and **Knowledge bases** (`#/simulation`, `#/knowledge-bases`)

**Simulation view** (main grid)

1. **News ticker** (header, right side) — RSS headlines from `/api/v1/news`; click a headline to read the article or create a scenario from that story
2. **Impact query** (left) — **Map view** toggle (**Live Flights** default = world fit, or **Scenario focus** = camera framed to the selected scenario bbox); pick a scenario (UK Airspace Closure, Port Strike LA, Suez Blockage, …) to run it; **Create scenario** opens a modal to describe a disruption in natural language; suggested prompts send follow-up questions through chat
3. **Map** (center) — Leaflet markers for seeded demo / live-seeded OpenSky entities; entity count and color legend in the panel
4. **Impact results** (right) — answer, score / value at risk, affected entities, diversions
5. **Chat bar** (bottom) — streaming RAG chat; the active knowledge-base name is shown above the input; vector store auto-matched to the active scenario when possible

**Knowledge bases view**

- Upload a name plus one or more `.txt` / `.md` / `.pdf` files
- Backend ingests into Llama Stack and registers the catalog
- After a successful upload, return to Simulation and pick the new store in chat if listed

**Create scenario modal**

- From Simulation, **Create scenario** opens a dialog: describe a disruption in natural language → propose draft → create in general-simulation
- On success, the new scenario is selected on the Simulation view

### What to expect behaviorally

- Map entities and impact answers reflect **seeded / simulated** supply-chain data, not a live ERP feed.
- Until you run `make seed-gen-sim`, the scenario list or map may be empty.
- Until Llama Stack and ingestion finish, chat may work without RAG context or vector-store options may be empty — check backend logs and `make ingest-status`.
- Impact query shows a loading state while waiting; errors appear inline in the panel.

---

## Suggested walkthrough

1. Open the **frontend Route** and confirm the Simulation view loads (backend healthy).
2. Seed demo data: `make seed-gen-sim` (add `make seed-opensky-live` if you want denser live aircraft).
3. Select **Port Strike LA** (or UK Airspace Closure / Suez Blockage) to run the scenario — review entities and diversions on the map and in Impact results.
4. Ask the chat: *“Summarize current critical alerts.”* (vector store may auto-select after ingest).
5. Open **Knowledge bases**, upload a short `.txt`, then ask a question grounded in that content.
6. Optionally use **Create scenario** to propose and add a custom disruption.

For troubleshooting pods, routes, and ingest jobs, use `make oc-status`, `make ingest-status`, and `make ingest-logs`.
