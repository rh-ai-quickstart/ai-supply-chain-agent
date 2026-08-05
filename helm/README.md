# Supply Chain Dashboard — Helm chart

Umbrella chart for the AI Supply Chain Agent quickstart. It deploys the application tier (backend, frontend, ingest job) plus shared AI/data subcharts from [ai-architecture-charts](https://github.com/rh-ai-quickstart/ai-architecture-charts), and optionally the [general-simulation](https://github.com/robertsandoval/general-simulation) platform as a subchart.

## What it deploys

- **pgvector** — PostgreSQL with the pgvector extension (agent RAG; kept even when gen-sim is enabled)
- **llama-stack** — Llama Stack API (chat, vector stores)
- **llm-service** — Model serving (e.g. Llama 3.2 1B)
- **general-simulation** — Optional subchart (own Postgres + Neo4j + API + ingestion); see below
- **backend** — Flask API
- **frontend** — React dashboard (nginx)
- **ingest** — Optional post-install Job (`ingest.enabled`)

## Prerequisites

- Helm 3.14+
- OpenShift CLI (`oc`) for cluster deploys
- A [Hugging Face token](https://huggingface.co/settings/tokens) (required for gated models)
- When `general-simulation.enabled: true`: chart repo [robertsandoval.github.io/general-simulation](https://robertsandoval.github.io/general-simulation) (after the first `chart-v*` publish), plus Neo4j auth Secret (below)

## Provide the Hugging Face token

The `llm-service` sub-chart reads the token from a Secret named `huggingface-secret` (key `HF_TOKEN`).

**Option A — use `helm/secrets.yaml`** (recommended for local development):

1. Copy the example file and edit:

```bash
cp helm/secrets.example.yaml helm/secrets.yaml
# Edit helm/secrets.yaml and add your HF token
```

2. Deploy as usual — the Makefile automatically applies `helm/secrets.yaml` if it exists:

```bash
make helm-install
```

**Option B — set it in `values.yaml`** (not recommended):

```yaml
llm-service:
  secret:
    hf_token: "<your-hf-token>"
```

**Option C — pre-create the Secret** (recommended for production; the token never touches a values file or secrets.yaml):

```bash
oc create secret generic huggingface-secret \
  -n supply-chain-dashboard \
  --from-literal=HF_TOKEN="<your-hf-token>"
```

## General Simulation subchart

Enabled by default via `general-simulation.enabled`. Gen-sim brings its **own** Postgres and Neo4j into the **same** namespace as this release. The agent keeps `pgvector` for its own RAG.

Before install, create Neo4j auth and set passwords in `helm/secrets.yaml` (see `secrets.example.yaml`):

```bash
oc create secret generic neo4j-auth \
  -n supply-chain-dashboard \
  --from-literal=NEO4J_AUTH="neo4j/<NEO4J_PASSWORD>"
```

Backend URL (same namespace):

```yaml
backend:
  env:
    GENERAL_SIMULATION_BASE_URL: "http://general-sim-api:8000"
```

To use a **standalone** gen-sim install in another project instead:

```yaml
general-simulation:
  enabled: false
backend:
  env:
    GENERAL_SIMULATION_BASE_URL: "http://general-sim-api.general-simulation.svc:8000"
```

## Install

From the repository root:

```bash
helm dependency update ./helm
helm upgrade --install supply-chain-dashboard ./helm \
  -f helm/values.yaml \
  --namespace supply-chain-dashboard \
  --create-namespace \
  --wait \
  --timeout 10m
```

Or use `make helm-deps` and `make helm-install` (see root `Makefile`).

## Verify

```bash
oc get pods,route -n supply-chain-dashboard
curl -s http://general-sim-api:8000/health   # from a pod in the namespace
```

## Customize

- **Models** — `global.models` and `llm-service.models`
- **GPU** — `llm-service.device` and per-model `device` (default is CPU in `values.yaml`)
- **Ingest** — `ingest.strategy` (`llamastack` | `langchain`), `ingest.enabled`, chunking under `ingest.*` for LangChain only
- **General simulation** — `general-simulation.enabled` and nested passwords / LLM settings

Full operator documentation: [README.md](../README.md) and [docs/WHAT_TO_EXPECT.md](../docs/WHAT_TO_EXPECT.md).
