# AI Supply Chain Agent

AI-powered supply chain impact simulation with a RAG chatbot to help operators monitor, analyze, and respond to global disruptions.

## Table of Contents

- [Overview](#overview)
- [Detailed description](#detailed-description)
  - [Architecture diagrams](#architecture-diagrams)
- [Requirements](#requirements)
  - [Minimum hardware requirements](#minimum-hardware-requirements)
  - [Minimum software requirements](#minimum-software-requirements)
  - [Required user permissions](#required-user-permissions)
- [Deploy](#deploy)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Validating the deployment](#validating-the-deployment)
  - [Delete](#delete)
- [Repository structure](#repository-structure)
- [References](#references)
- [Technical details](#technical-details)
- [Tags](#tags)

## Overview

Global supply chains are complex and exposed to frequent disruptions — port strikes, airspace closures, blocked shipping lanes, and more. When something goes wrong, operators must quickly understand which entities are affected, how much value is at risk, and where to divert shipments.

This quickstart deploys an interactive supply chain impact workspace on OpenShift AI. Operators run natural-language what-if impact scenarios, inspect affected entities and recommended diversions on a map, and ask questions to a RAG chatbot grounded in curated risk documents. After deployment, operators can monitor, analyze, and respond to disruptions from a single dashboard.

## Detailed description

Global supply chains are increasingly exposed to cascading disruption. Port strikes, airspace closures, and blocked shipping lanes can spread quickly: when one link breaks, operators must determine which shipments, suppliers, and routes are affected, quantify the impact, and decide where to divert traffic — often within minutes. Doing this across spreadsheets, emails, and scattered news feeds is slow and error-prone.

This quickstart addresses that problem by pairing a logistics simulation engine with a Retrieval-Augmented Generation (RAG) chatbot. Operators run natural-language what-if impact queries against seeded scenarios, review the impact score, value at risk, affected entities, and recommended diversions on an interactive Leaflet map, and ask follow-up questions in a chat session grounded in curated risk documents. The same workspace supports uploading additional knowledge bases at runtime.

Key capabilities:

- **Impact simulation**: Run a natural-language impact query against a seeded scenario (port strike, airspace closure, Suez blockage) and review score, value at risk, affected entities, and recommended diversions on a map.
- **RAG chatbot**: Streaming chat with per-scenario history; the UI auto-matches a Llama Stack vector store by scenario keywords.
- **Knowledge bases**: Upload `.txt`/`.md`/`.pdf` documents at runtime; a Helm post-install job also loads bundled risk analyses into Llama Stack vector stores (`ingest.strategy: llamastack`) or optionally PGVector (`langchain`).

For a longer product narrative (audience, problem statement, and demo scenario catalog), see [DETAILED_DESCRIPTION.md](DETAILED_DESCRIPTION.md).

### Architecture diagrams

The quickstart runs on OpenShift as a Helm umbrella chart (`supply-chain-dashboard`). Operators reach the impact workspace through a standalone Route. The Flask backend proxies general-simulation impact queries, RAG chat, and knowledge-base management; Llama Stack, PGVector, and the general-simulation subchart provide inference, retrieval, and spatial impact.

#### Deployment (OpenShift)

```mermaid
flowchart TB
  subgraph users["Operators"]
    U1["Browser — impact workspace"]
  end

  subgraph ocp["OpenShift cluster"]
    subgraph ns["Namespace: supply-chain-dashboard"]
      subgraph routes["Routes"]
        R_FE["supply-chain-dashboard-frontend"]
        R_BE["supply-chain-dashboard-backend"]
      end

      FE["Frontend<br/>React + nginx :8080"]
      BE["Backend<br/>Flask API :5001"]

      subgraph jobs["Jobs"]
        ING["Ingest Job<br/>risk docs → embeddings"]
      end

      subgraph data["Data & AI (gen-sim subchart)"]
        PG[("PGVector<br/>PostgreSQL + pgvector")]
        LS["Llama Stack<br/>:8321"]
        VLLM["llm-service<br/>in-cluster vLLM"]
        GS["General Simulation<br/>API + Neo4j + Postgres"]
      end
    end
  end

  U1 --> R_FE --> FE
  FE -->|"same-origin /api/* proxy"| BE
  U1 -.->|"direct API (curl, tools)"| R_BE
  R_BE --> BE

  BE -->|"impact query / GeoJSON"| GS
  BE -->|"RAG similarity search"| PG
  BE -->|"chat, vector stores, ingest API"| LS
  LS --> VLLM
  GS --> LS

  ING -->|"llamastack or langchain strategy"| LS
  ING -.->|"langchain path"| PG

  classDef user fill:#e8f4fc,stroke:#1a73e8,color:#111
  classDef app fill:#f3e8fd,stroke:#7c3aed,color:#111
  classDef data fill:#ecfdf5,stroke:#059669,color:#111
  classDef route fill:#fff7ed,stroke:#ea580c,color:#111
  classDef ext fill:#eff6ff,stroke:#2563eb,color:#111
  class U1 user
  class FE,BE,ING app
  class PG,LS,VLLM,GS data
  class R_FE,R_BE route
```

#### Impact simulation and RAG chat

```mermaid
sequenceDiagram
  autonumber
  participant UI as Frontend
  participant BE as Backend (Flask)
  participant GS as General Simulation
  participant PG as PGVector
  participant LS as Llama Stack
  participant VLLM as llm-service (vLLM)

  Note over UI,VLLM: Impact map
  UI->>BE: GET /api/v1/general-simulation/scenarios
  BE->>GS: list scenarios
  GS-->>BE: scenario IDs
  BE-->>UI: picker options
  UI->>BE: GET /api/v1/general-simulation/entities/geojson
  BE->>GS: GeoJSON features
  GS-->>UI: map markers (via BE)

  Note over UI,VLLM: Impact query
  UI->>BE: POST /api/v1/general-simulation/query
  BE->>GS: NL impact question + scenario
  GS-->>BE: score, VaR, entities, diversions
  BE-->>UI: Impact results + map highlights

  Note over UI,VLLM: RAG chat (SSE stream)
  UI->>BE: POST /api/v1/chat
  alt Off-topic prompt
    BE-->>UI: Guardrail reply
  else RAG / tools path
    BE->>PG: Similarity search (optional fallback)
    BE->>LS: Chat completion (augmented prompt)
    LS->>VLLM: Inference
    VLLM-->>LS: Tokens
    LS-->>BE: Completion / stream chunks
    BE-->>UI: Markdown answer
  end
```

## Requirements

### Minimum hardware requirements

| Resource | Default (`llm-service`) | Optional MaaS |
|----------|-------------------------|---------------|
| CPU | 8+ vCPU | 4 vCPU |
| Memory | 32+ GB (CPU vLLM needs more) | 16 GB |
| GPU | Recommended (or CPU with AVX-512) | Not required |
| Storage | 50 GB (model weights + PGVector) | 20 GB |

> **Note**: Default `helm/values.yaml` enables gen-sim **llm-service** under `general-simulation`. Model selection (`general-simulation.global.models`, `api.models.generation`) is owned by the gen-sim subchart; the supply-chain backend reads `general-simulation.api.models.generation` for `LLAMA_STACK_MODEL`. Set `general-simulation.llm-service.secret.hf_token` in `helm/secrets.yaml`.

**Optional MaaS:** configure `general-simulation.global.models.external-model` and disable `llm-service` (see `helm/README.md`).

### Minimum software requirements

| Component | Version |
|-----------|---------|
| OpenShift | 4.21+ |
| OpenShift AI | 3.4+ |
| Helm | 3.14+ |
| Llama Stack | via `general-simulation` subchart (from [general-simulation](https://github.com/robertsandoval/general-simulation) chart 0.0.1) |
| Python | 3.12 |
| Node.js | 22 (frontend builds) |
| `oc` CLI | Recommended for deploy status and troubleshooting |

### Required user permissions

This quickstart can be deployed by any user with **namespace admin** in the target project. Deploying the main Helm chart creates Routes, Deployments, Services, and a Job — no cluster admin access is required.

## Deploy

### Prerequisites

Before deploying, ensure you have:

- Access to a Red Hat OpenShift cluster with OpenShift AI 3.4+ installed
- `oc` CLI (OpenShift 4.21+) installed and authenticated
- `helm` CLI (3.14+) installed
- A [Hugging Face token](https://huggingface.co/settings/tokens) for gen-sim `llm-service` (gated models; set in `helm/secrets.yaml`)
- Optional: MaaS only if you disable `llm-service` and configure `general-simulation.global.models.external-model`
- Sibling checkout of [general-simulation](https://github.com/robertsandoval/general-simulation) at `../general-simulation` for `make seed-gen-sim` (recommended for map data)

### Installation

Defaults used below (overridable on `make`, e.g. `make helm-install NAMESPACE=my-ns`):

| Setting | Default |
|---------|---------|
| Helm chart | `./helm` |
| Release name | `supply-chain-dashboard` |
| Namespace | `supply-chain-dashboard` |
| Values file | `helm/values.yaml` |
| CI/CD Values File | `helm/values-kind.yaml` |

### Kind / local Kubernetes smoke

The same Helm chart installs on Kind for CI (`.github/workflows/kind-helm-smoke.yml`) and local smoke tests. Supply-chain images are built into `localhost:5001` via per-component `image.repository` (`HELM_KIND_IMAGE_SETS`); platform images use `general-simulation.global.registry` in `values-kind.yaml`.

| Environment | Minimum RAM | Notes |
|-------------|-------------|-------|
| GHA `ubuntu-latest` | ~7Gi allocatable | CI path — no extra setup |
| Local Podman + Kind | **8Gi Podman VM** | Neo4j requests 2Gi (official chart minimum) |

```bash
make kind-preflight                              # check RAM before local smoke
make local-kind-smoke-test                       # full cluster + install + verify
make local-kind-smoke-test LOCAL_KIND_SMOKE_ARGS='--recreate --skip-build'
```

If preflight fails on a 2Gi Podman machine, resize the VM and recreate the cluster — see [`helm/README.md`](helm/README.md#kind--local-kubernetes-smoke).

Run `make help` for the full target list.

1. Clone the repository:

```bash
git clone https://github.com/rh-ai-quickstart/ai-supply-chain-agent.git
cd ai-supply-chain-agent
```

2. Create a new OpenShift project:

```bash
oc new-project supply-chain-dashboard
```

3. Set your Hugging Face token for `llm-service`.

**Default — use `helm/secrets.yaml`** (recommended):

```bash
cp helm/secrets.example.yaml helm/secrets.yaml
# Edit helm/secrets.yaml and set general-simulation.llm-service.secret.hf_token
```

**Override at install:**

```bash
helm upgrade --install supply-chain-dashboard ./helm \
  -f helm/values.yaml \
  --set general-simulation.llm-service.secret.hf_token="<your-hf-token>" \
  --namespace supply-chain-dashboard \
  --create-namespace \
  --wait \
  --timeout 15m
```

**Optional MaaS:** configure under `general-simulation` only — see `helm/README.md`.

Everything else in `helm/values.yaml` works with the chart defaults (images, PGVector demo credentials, in-cluster API proxy, Llama Stack URLs).

4. Install Helm dependencies:

```bash
helm dependency update ./helm
```

**Makefile alternative:**

```bash
make helm-deps
```

5. Deploy the application.

#### Default: in-cluster `llm-service` (via gen-sim)

`helm/values.yaml` enables `general-simulation.llm-service`. After setting the HF token (step 3):

```bash
helm upgrade --install supply-chain-dashboard ./helm \
  -f helm/values.yaml \
  -f helm/secrets.yaml \
  --namespace supply-chain-dashboard \
  --create-namespace \
  --set global.registry=quay.io/<your-org> \
  --wait \
  --timeout 15m
```

**Makefile:**

```bash
make helm-upgrade-install REGISTRY=quay.io/<your-org>
```

`global.registry` sets images for supply-chain (backend, frontend, ingest) **and** the general-simulation subchart (postgres, api, bootstrap, ingestion). The Makefile passes the same via `REGISTRY=`.

#### Optional: MaaS / external model

Configure only under `general-simulation`:

```yaml
general-simulation:
  global:
    models:
      llama-3-2-3b-instruct:
        enabled: false
      external-model:
        enabled: true
  llm-service:
    enabled: false
  api:
    models:
      generation: external-model/<your-model-id>
```

Set `general-simulation.global.models.external-model.apiToken` in `helm/secrets.yaml`, then install.

#### Custom OpenAI-compatible endpoint

To point at a non-default OpenAI-compatible endpoint:

```bash
helm upgrade --install supply-chain-dashboard ./helm \
  -f helm/values.yaml \
  --set general-simulation.global.models.external-model.id=<your-model-id> \
  --set general-simulation.global.models.external-model.url=https://<your-endpoint>/v1 \
  --set general-simulation.global.models.external-model.apiToken=<your-token> \
  --set general-simulation.api.models.generation=external-model/<your-model-id> \
  --namespace supply-chain-dashboard \
  --create-namespace \
  --wait \
  --timeout 10m
```

### Validating the deployment

1. Check all pods are running:

```bash
oc get pods -n supply-chain-dashboard
```

2. Get the application URL:

```bash
oc get route supply-chain-dashboard-frontend -n supply-chain-dashboard -o jsonpath='https://{.spec.host}{"\n"}'
```

**Makefile alternative:**

```bash
make oc-status
```


3. Open the frontend Route URL in your browser. See [What to expect after deployment](./docs/WHAT_TO_EXPECT.md) for the Simulation / Knowledge bases walkthrough.

4. Seed general-simulation map data (required for scenarios and markers). Gen-sim's in-cluster OpenSky job is disabled by default — OpenSky often blocks hyperscaler IPs. From a laptop with `oc` login and a sibling general-simulation checkout:

```bash
make seed-gen-sim
# optional denser live aircraft (OpenSky pulled on your laptop → cluster DBs)
make seed-opensky-live GEN_SIM_NAMESPACE=supply-chain-dashboard
# or: make seed
```

5. (Optional) Re-run knowledge-base ingestion without a full Helm upgrade:

```bash
make ingest
make ingest-status
make ingest-logs
```

### Delete

To completely remove the deployment:

1. Uninstall the Helm release:

```bash
helm uninstall supply-chain-dashboard --namespace supply-chain-dashboard
```

**Makefile alternative:**

```bash
make helm-uninstall
```

2. Delete the project:

```bash
oc delete project supply-chain-dashboard
```

## Repository structure

```
.
├── app/                            # Application source code
│   ├── backend/                    # Flask API (runtime image)
│   │   ├── api/
│   │   │   ├── main.py             # App entry point
│   │   │   ├── app_factory.py      # Flask app + blueprint registration
│   │   │   ├── requirements.txt
│   │   │   ├── Containerfile
│   │   │   ├── clients/            # Llama Stack, PGVector, gen-sim, OpenSky, news
│   │   │   ├── routes/             # HTTP blueprints (chat, gen-sim, KB, …)
│   │   │   ├── services/           # Chat, impact proxy, scenario create, RAG
│   │   │   └── repositories/       # JSON file stores for KB / simulations catalog
│   │   └── ingestion/              # Knowledge-base ingestion CLI (ingest image)
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── loaders/document_loader.py
│   │       ├── services/
│   │       │   ├── ingestion_service.py
│   │       │   └── llamastack_ingestion_service.py
│   │       └── knowledge_base/     # Bundled .txt risk documents
│   └── frontend/                   # React + Vite SPA
│       ├── index.html
│       ├── package.json
│       ├── vite.config.js
│       ├── Containerfile
│       └── src/
│           ├── App.jsx
│           ├── components/         # ImpactSimulationPage, ImpactMapPanel,
│           │                       # ImpactQueryPanel, ImpactResultsPanel, ChatBar,
│           │                       # KnowledgeBasesPage, CreateScenarioModal, NewsTicker
│           ├── hooks/              # useImpactSimulation, useChatSession, useHashRoute, …
│           └── services/           # apiClient, generalSimulationService, …
├── helm/                           # Helm umbrella chart
│   ├── Chart.yaml                  # Chart metadata
│   ├── values.yaml                 # Default configuration values
│   └── templates/                  # Kubernetes resource templates
├── scripts/
│   ├── seed-gen-sim-demo.sh        # Laptop → cluster Neo4j+Postgres demo seed
│   └── seed-opensky-live.sh        # Laptop OpenSky pull → cluster DBs
├── docs/
│   └── WHAT_TO_EXPECT.md           # Post-deployment walkthrough
└── README.md
```

## References

- [What to expect after deployment?](./docs/WHAT_TO_EXPECT.md)
- [Detailed description](./DETAILED_DESCRIPTION.md)
- [Contributing](./CONTRIBUTING.md)
- [Llama Stack documentation](https://llama-stack.readthedocs.io)
- [LangChain PGVector integration](https://python.langchain.com/docs/integrations/vectorstores/pgvector/)
- [React Leaflet](https://react-leaflet.js.org/)
- [OpenShift AI documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed)

## Technical details

### Backend API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Liveness probe |
| `GET` | `/readyz` | Readiness (dependency checks) |
| `GET` | `/api/v1/version` | Build metadata |
| `GET` | `/api/v1/general-simulation/scenarios` | Scenario IDs for the impact picker |
| `POST` | `/api/v1/general-simulation/query` | Natural-language impact query |
| `GET` | `/api/v1/general-simulation/entities/geojson` | Map entity GeoJSON |
| `POST` | `/api/v1/chat` | RAG-augmented chat (SSE when `stream: true`) |
| `GET` | `/api/v1/vector_stores` | List Llama Stack vector stores (chat picker) |
| `GET` / `POST` | `/api/v1/knowledge-bases` | List or upload UI-managed knowledge bases |
| `POST` | `/api/v1/scenarios/propose` | Propose a scenario draft from NL |
| `POST` | `/api/v1/scenarios` | Create a scenario in general-simulation |
| `GET` | `/api/v1/news` | RSS headlines for the news ticker |

### Environment variables

**Helm (`helm/secrets.yaml`)** — default: `general-simulation.llm-service.secret.hf_token`. Optional MaaS: `general-simulation.global.models.external-model.apiToken`. Do not use `${env.VAR}` in tokens.

**Backend**

| Variable | Description | Default |
|----------|-------------|---------|
| `LLAMA_STACK_URL` | Llama Stack base URL | — |
| `LLAMA_STACK_MODEL` | Model identifier (from `general-simulation.api.models.generation`) | — |
| `EMBED_MODEL` | Embedding model (default: `general-simulation.api.models.embedding`) | — |
| `PG_HOST` | PostgreSQL host | — |
| `PG_PORT` | PostgreSQL port | `5432` |
| `PG_USER` | PostgreSQL user | — |
| `PG_PASSWORD` | PostgreSQL password | — |
| `PG_DB` | PostgreSQL database name | — |
| `GENERAL_SIMULATION_BASE_URL` | General-simulation API base URL | `http://general-sim-api:8000` (chart) |
| `NEWS_FEED_URLS` | Optional custom RSS feeds (`Name\|url` pairs) | empty → BBC/Guardian defaults |

**Ingestion job (additional)**

| Variable | Description | Default |
|----------|-------------|---------|
| `INGEST_STRATEGY` | `llamastack` (server-side) or `langchain` (PGVector) | `llamastack` (chart default) |
| `KNOWLEDGE_BASE_DIR` | Path to `.txt` source documents | `knowledge_base` |
| `INGEST_CHUNK_SIZE` | Chunk size (`langchain` strategy only) | `1000` |
| `INGEST_CHUNK_OVERLAP` | Chunk overlap (`langchain` strategy only) | `200` |
| `INGEST_DROP_OLD` | Drop existing collection before ingestion (`langchain` only) | `true` |
| `INGEST_GLOB` | Glob pattern for source files | `**/*.txt` |

**Frontend**

| Variable | Description | Default |
|----------|-------------|---------|
| `BACKEND_UPSTREAM` | nginx `/api` proxy target (set on the frontend pod at runtime) | `http://<release>-backend:5001` |
| `VITE_DEV_API_PROXY_TARGET` | Local `pnpm dev` proxy target for `/api` | `http://127.0.0.1:5001` |

### Helm chart overrides

| Optional override | When you need it |
|-------------------|------------------|
| `global.registry` / `global.imageTag` | Point all images at your registry (supply-chain + gen-sim subchart) |
| `backend.image.name` / `tag`, `frontend.image.*`, `ingest.image.*` | Per-component image name or tag override |
| `frontend.apiProxyUpstream` | Backend Service is not `http://<release>-backend:<port>` in the release namespace |
| `general-simulation.*` (models, llm-service, api.models.generation) | All inference config — backend reads `api.models.generation` |
| `backend.env.EMBED_MODEL` | Optional override; default is `general-simulation.api.models.embedding` |
| `backend.env.LLAMA_STACK_URL` | Release installed outside `supply-chain-dashboard` namespace |
| `general-simulation.postgres.postgres.password` (+ matching `general-simulation.*.postgres.password`) | Shared Postgres credentials (must stay in sync) |
| `ingest.strategy` | `langchain` for PGVector ingest instead of default `llamastack` |
| `general-simulation.api.llm.*` | Gen-sim OpenAI endpoint / model overrides (`apiKey` in secrets) |
| `general-simulation.ingestion.enabled` | Keep `false` on AWS/hyperscaler clusters (OpenSky IP block); seed from laptop instead |

### Building your own images

Build all application images:

```bash
make build
```

Or build and push in one step (after `make login` to your registry):

```bash
make release REGISTRY=quay.io/<your-org>
make helm-upgrade-install REGISTRY=quay.io/<your-org>
```

`REGISTRY` maps to `--set global.registry=...` for all supply-chain and gen-sim images.

Individual images:

```bash
make build-backend build-ingest build-frontend
make push-backend push-ingest push-frontend
```

Override tags or registry as needed, e.g. `make build-backend BACKEND_TAG=v1 REGISTRY=quay.io/myorg`.

### Dependencies

**Frontend:** React 19 + Vite 7 + pnpm; Leaflet 1.9 + `react-leaflet` 5 (impact map); react-markdown (streaming chat / impact answers).

**Backend:** Flask + `flask-cors`; `openai` (Llama Stack OpenAI-compatible client); LangChain (`langchain`, `langchain-community`, `langchain-text-splitters`, `langchain-openai`, `langchain-postgres`) for document loading, splitting, embedding, and PGVector integration; `psycopg[binary]` (PostgreSQL driver).

## Tags

- **Title**: AI Supply Chain Agent
- **Description**: AI-powered supply chain impact simulation with a RAG chatbot to help operators monitor, analyze, and respond to global disruptions.
- **Industry**: Manufacturing
- **Product**: OpenShift AI
- **Use case**: AI agents, RAG, supply chain intelligence
- **Partner**: N/A
- **Contributor org**: Red Hat
