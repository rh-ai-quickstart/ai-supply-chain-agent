# Supply Chain Dashboard — Helm chart

Umbrella chart for the AI Supply Chain Agent quickstart. It deploys the application tier (backend, frontend, ingest job) plus shared AI/data subcharts from [ai-architecture-charts](https://github.com/rh-ai-quickstart/ai-architecture-charts), and optionally the [general-simulation](https://github.com/robertsandoval/general-simulation) platform as a subchart.

## What it deploys

- **pgvector** — PostgreSQL with the pgvector extension (agent RAG; kept even when gen-sim is enabled)
- **llama-stack** — Llama Stack API (chat, vector stores); default inference via MaaS / `external-model`
- **llm-service** — Optional in-cluster model serving (disabled by default)
- **general-simulation** — Optional subchart (own Postgres + Neo4j + API + ingestion); see below
- **backend** — Flask API
- **frontend** — React dashboard (nginx)
- **ingest** — Optional post-install Job (`ingest.enabled`)

## Prerequisites

- Helm 3.14+
- OpenShift CLI (`oc`) for cluster deploys
- A MaaS / LiteMaaS API token (default path: `global.models.external-model.apiToken` in `secrets.yaml`)
- A [Hugging Face token](https://huggingface.co/settings/tokens) only if you re-enable `llm-service` for gated models
- When `general-simulation.enabled: true`: Neo4j auth Secret (below)

## Provide the MaaS API token (default)

Set a **literal** token on `global.models.external-model.apiToken` (via `helm/secrets.yaml` or `--set`). Do not use `${env.VAR}` — the llama-stack `wait-for-models` init script expands that unquoted and bash fails with `bad substitution`.

**Option A — use `helm/secrets.yaml`** (recommended for local development):

1. Copy the example file and edit:

```bash
cp helm/secrets.example.yaml helm/secrets.yaml
# Edit helm/secrets.yaml and set global.models.external-model.apiToken
```

2. Deploy as usual — the Makefile automatically applies `helm/secrets.yaml` if it exists:

```bash
make helm-install
```

**Option B — pass at install time:**

```bash
helm upgrade --install supply-chain-dashboard ./helm \
  -f helm/values.yaml \
  --set global.models.external-model.apiToken="<your-maas-token>" \
  --namespace supply-chain-dashboard \
  --create-namespace
```

## Optional: local model (Hugging Face token)

Only when `llm-service.enabled: true`. The `llm-service` sub-chart reads Secret `huggingface-secret` (key `HF_TOKEN`), or `llm-service.secret.hf_token` from `secrets.yaml`.

```bash
oc create secret generic huggingface-secret \
  -n supply-chain-dashboard \
  --from-literal=HF_TOKEN="<your-hf-token>"
```

## General Simulation subchart

Enabled by default via `general-simulation.enabled`. Gen-sim brings its **own** Postgres and Neo4j into the **same** namespace as this release. The agent keeps `pgvector` for its own RAG.

**Gen-sim does not use MaaS.** It calls OpenAI (`api.llm.backend: openai`) with `apiKey` from `helm/secrets.yaml`. Override `baseUrl` if you want a different OpenAI-compatible endpoint.

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

- **MaaS** — `global.models.external-model` (`id`, `url`, `apiToken` via secrets)
- **Local models** — re-enable `llm-service` and `global.models.<model>.enabled`
- **GPU** — `llm-service.device` and per-model `device` when local serving is on
- **Ingest** — `ingest.strategy` (`llamastack` | `langchain`), `ingest.enabled`, chunking under `ingest.*` for LangChain only
- **General simulation** — `general-simulation.enabled` and nested passwords / OpenAI `llm.apiKey` (not MaaS)

Full operator documentation: [README.md](../README.md) and [docs/WHAT_TO_EXPECT.md](../docs/WHAT_TO_EXPECT.md).
