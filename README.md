# AI Supply Chain Agent

An AI-powered supply chain intelligence dashboard that combines real-time logistics simulation with a Retrieval-Augmented Generation (RAG) chatbot to help operators monitor, analyze, and respond to global supply chain disruptions.

## Table of contents

- [Detailed description](#detailed-description)
- [Architecture diagrams](#architecture-diagrams)
- [Requirements](#requirements)
- [Deploy](#deploy)
- [References](#references)
- [Technical details](#technical-details)
- [Tags](#tags)

## Detailed description

This quickstart deploys an interactive supply chain operations dashboard backed by a Llama Stack LLM and a PGVector knowledge base. Operators can monitor KPIs (inventory levels, revenue, route efficiency), trigger simulated disruption scenarios (port strikes, geopolitical events), and ask natural-language questions via a built-in RAG chatbot that draws on a curated supply-chain risk knowledge base.

Key capabilities:
- **Live dashboard**: KPI bar, demand and revenue charts, a Leaflet logistics map (global / regional / air-freight views), system health metrics, and an alerts panel — all refreshed every 15 seconds.
- **Scenario simulation**: Select a disruption scenario (e.g. port strike, geopolitical tension) and optionally enable route optimization; the backend updates dashboard state and returns an AI-generated analysis.
- **RAG chatbot**: A chat sidebar sends questions to a Flask API that performs similarity search over PGVector, builds a context-augmented prompt, and calls the Llama Stack LLM.
- **Ingestion pipeline**: A Helm post-install job chunks `.txt` knowledge-base documents and embeds them into PGVector using the configured embedding model.

### Architecture diagrams

<!-- TODO: add architecture diagram — put images in docs/images/ -->

## Requirements

### Minimum hardware requirements

| Resource | Minimum |
|----------|---------|
| GPU | 1× NVIDIA A10G (24 GB VRAM) or equivalent for LLM inference |
| CPU | 8 vCPU |
| RAM | 32 GB |
| Storage | 50 GB (model weights + PGVector data) |

### Minimum software requirements

| Component | Tested version |
|-----------|---------------|
| OpenShift | 4.16+ |
| OpenShift AI | 2.13+ |
| Helm | 3.14+ |
| Llama Stack | compatible with `llama-stack` Helm chart included in `chart/` |
| Python | 3.12 |
| Node.js | 22 (frontend build only) |

### Required user permissions

- **OpenShift cluster-admin** role (or namespace admin with ability to create Routes, PersistentVolumeClaims, and Jobs) is required to deploy the Helm chart.
- A standard user account is sufficient to interact with the deployed dashboard.

## Deploy

### 1. Clone the repository

```bash
git clone https://github.com/rh-aiservices-bu/ai-supply-chain-agent.git
cd ai-supply-chain-agent
```

### 2. Configure values

Copy and edit the Helm values file:

```bash
cp chart/values.yaml chart/my-values.yaml
```

Set at minimum:

| Value | Description |
|-------|-------------|
| `backend.image.repository` / `tag` | Backend container image |
| `frontend.image.repository` / `tag` | Frontend container image |
| `llama_stack.model` | Llama Stack model identifier |
| `embed_model` | Embedding model identifier |
| `pgvector.*` | PostgreSQL connection details |

### 3. Deploy with Helm

```bash
helm upgrade --install ai-supply-chain-agent ./chart \
  -f chart/my-values.yaml \
  --namespace ai-supply-chain \
  --create-namespace
```

The Helm chart deploys:
- **Backend** — Flask API (port 5001)
- **Frontend** — React SPA served by nginx (port 8080)
- **PGVector** — PostgreSQL + pgvector extension
- **Llama Stack** — LLM inference server
- **Ingest Job** — post-install Helm hook that loads the knowledge base into PGVector

### 4. Access the dashboard

After all pods are running, retrieve the frontend Route:

```bash
oc get route frontend -n ai-supply-chain
```

Open the displayed URL in your browser.

### Delete

To remove all resources:

```bash
helm uninstall ai-supply-chain-agent --namespace ai-supply-chain
oc delete namespace ai-supply-chain
```

## References

- [Llama Stack documentation](https://llama-stack.readthedocs.io)
- [LangChain PGVector integration](https://python.langchain.com/docs/integrations/vectorstores/pgvector/)
- [React Leaflet](https://react-leaflet.js.org/)
- [Chart.js](https://www.chartjs.org/)
- [OpenShift AI documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed)

## Technical details

### Repository layout

```
app/
├── backend/               # Python Flask API
│   ├── main.py            # App entry point and route definitions
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── clients/
│   │   ├── llama_stack_client.py   # OpenAI-compatible LLM client
│   │   └── vector_store_client.py  # PGVector / LangChain client
│   ├── services/
│   │   ├── chat_service.py         # RAG pipeline + guardrails
│   │   ├── dashboard_service.py    # KPI / alert / chart state
│   │   └── route_service.py        # Route optimization logic
│   └── ingest/                     # Knowledge-base ingestion CLI
│       ├── main.py
│       ├── config.py
│       ├── loaders/document_loader.py
│       ├── services/ingestion_service.py
│       └── knowledge_base/         # .txt source documents
└── frontend/              # React + Vite SPA
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── Dockerfile
    └── src/
        ├── App.jsx
        ├── components/    # AlertsPanel, ChatBar, DashboardHeader,
        │                  # DemandChartPanel, KpiBar, LogisticsMapPanel,
        │                  # RevenueChartPanel, SimulationPanel, SystemHealthPanel
        ├── hooks/
        │   └── useDashboardState.js   # Polls /api/v1/state every 15 s
        └── services/
            ├── apiClient.js           # fetch wrappers (VITE_API_BASE_URL)
            ├── dashboardService.js    # API call helpers
            └── dashboardMappers.js    # Backend state → UI data shapes
```

### Backend API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Liveness probe |
| `GET` | `/api/v1/state` | Full dashboard state (KPIs, alerts, charts, map) |
| `POST` | `/api/v1/trigger-event` | Trigger a disruption event for a given map view |
| `POST` | `/api/v1/simulate` | Run a named scenario with optional route optimization |
| `POST` | `/api/v1/chat` | RAG-augmented chat with the LLM |

### Environment variables

**Backend**

| Variable | Description | Default |
|----------|-------------|---------|
| `LLAMA_STACK_URL` | Llama Stack base URL | — |
| `LLAMA_STACK_MODEL` | Model identifier | — |
| `EMBED_MODEL` | Embedding model identifier | — |
| `PG_HOST` | PostgreSQL host | — |
| `PG_PORT` | PostgreSQL port | `5432` |
| `PG_USER` | PostgreSQL user | — |
| `PG_PASSWORD` | PostgreSQL password | — |
| `PG_DB` | PostgreSQL database name | — |

**Ingestion job (additional)**

| Variable | Description | Default |
|----------|-------------|---------|
| `KNOWLEDGE_BASE_DIR` | Path to `.txt` source documents | `ingest/knowledge_base` |
| `INGEST_CHUNK_SIZE` | Token chunk size | `500` |
| `INGEST_CHUNK_OVERLAP` | Chunk overlap | `50` |
| `INGEST_DROP_OLD` | Drop existing collection before ingestion | `false` |
| `INGEST_GLOB` | Glob pattern for source files | `**/*.txt` |

**Frontend**

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend base URL (set at build time) | `http://backend:5001` |

### Frontend dependencies

- **React 19** + **Vite 7**
- **Chart.js 4** + `react-chartjs-2` — demand and revenue charts
- **Leaflet 1.9** + `react-leaflet 5` — logistics map

### Backend dependencies

- **Flask** + `flask-cors`
- **openai** — Llama Stack OpenAI-compatible client
- **LangChain** (`langchain`, `langchain-community`, `langchain-text-splitters`, `langchain-openai`, `langchain-postgres`) — document loading, splitting, embedding, PGVector integration
- **psycopg[binary]** — PostgreSQL driver

## Tags

- **Title**: AI Supply Chain Agent
- **Description**: AI-powered supply chain dashboard with RAG chatbot, disruption simulation, and real-time logistics monitoring on OpenShift AI.
- **Industry**: Manufacturing / Logistics
- **Product**: OpenShift AI, OpenShift
- **Use case**: AI agents, RAG, supply chain intelligence
- **Contributor org**: Red Hat
